import xmltodict
import json


class Structure:  # structure为xml根节点的ViewInfo列表
    def get_structure_from_xml(self, xml_path):
        node_queue = []
        with open(xml_path, 'r', encoding="utf-8") as f:
            xml_dict = xmltodict.parse(f.read())

        if "node" in xml_dict["hierarchy"].keys():
            if isinstance(xml_dict["hierarchy"]["node"], list):
                for sub_node in xml_dict["hierarchy"]["node"]:
                    if 'com.android.systemui' not in sub_node['@resource-id'] and 'com.android.systemui' not in sub_node['@package']:
                        node_queue.append(self.get_view_from_node(sub_node))
            elif 'com.android.systemui' not in xml_dict["hierarchy"]["node"]['@resource-id'] and 'com.android.systemui' not in xml_dict["hierarchy"]["node"]['@package']:
                node_queue.append(self.get_view_from_node(xml_dict["hierarchy"]["node"]))

        return node_queue

    def get_view_from_node(self, node):
        temp = node['@bounds']
        for i in range(len(temp)):
            if temp[i] == ']':
                temp = temp[0:i + 1] + "," + temp[i + 1:]
                break
        pos = eval(temp)
        x = pos[0][0]
        y = pos[0][1]
        width = pos[1][0] - pos[0][0]
        height = pos[1][1] - pos[0][1]
        class_name = node['@class']
        index = node['@index']
        view = ViewInfo(x, y, width, height, class_name, index)
        if "node" in node.keys():
            if isinstance(node["node"], list):
                for sub_node in node["node"]:
                    if 'com.android.systemui' not in sub_node['@resource-id'] and 'com.android.systemui' not in sub_node['@package']:
                        view.childs.append(self.get_view_from_node(sub_node))
            elif 'com.android.systemui' not in node["node"]['@resource-id'] and 'com.android.systemui' not in node["node"]['@package']:
                view.childs.append(self.get_view_from_node(node["node"]))
        return view


class ViewInfo:  # 部件信息，用于比较相似度
    def __init__(self, x, y, width, height, class_name, index):
        self.x = x  # 部件左上点x轴坐标
        self.y = y  # 部件左上点y轴坐标
        self.width = width  # 部件宽度
        self.height = height  # 部件高度
        self.class_name = class_name  # 部件类名
        self.view_index = index  # 部件index序号
        self.childs = []  # 部件子部件列表


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ViewInfo):
            return {
                "x": obj.x,
                "y": obj.y,
                "width": obj.width,
                "height": obj.height,
                "class_name": obj.class_name,
                "view_index": obj.view_index,
                "childs": [self.default(child) for child in obj.childs]
            }
        return super().default(obj)


def custom_decoder(dct):
    if isinstance(dct, dict):
        if 'x' in dct and 'y' in dct and 'width' in dct and 'height' in dct and 'class_name' in dct and 'view_index' in dct:
            view_info = ViewInfo(dct['x'], dct['y'], dct['width'], dct['height'], dct['class_name'], dct['view_index'])
            if 'childs' in dct:
                view_info.childs = [custom_decoder(child) for child in dct['childs']]
            return view_info
    return dct


class MatchUtil:
    def __init__(self):
        # assign weight of each part
        self.p1 = self.p2 = self.p3 = self.p4 = 1 / 4
        # the threshold of viewInfo
        self.viewInfoThreshold = 0.6

    def obtain_view_similarity(self, view_info1, view_info2):
        part_x_min = min(view_info1.x, view_info2.x)
        part_x_max = max(view_info1.x, view_info2.x)
        if part_x_max == 0:
            part_x_min += 1
            part_x_max += 1
        part_y_min = min(view_info1.y, view_info2.y)
        part_y_max = max(view_info1.y, view_info2.y)
        if part_y_max == 0:
            part_y_min += 1
            part_y_max += 1
        part_w_min = min(view_info1.width, view_info2.width)
        part_w_max = max(view_info1.width, view_info2.width)
        if part_w_max == 0:
            part_w_min += 1
            part_w_max += 1
        part_h_min = min(view_info1.height, view_info2.height)
        part_h_max = max(view_info1.height, view_info2.height)
        if part_h_max == 0:
            part_h_min += 1
            part_h_max += 1
        res = (self.p1 * part_x_min / part_x_max +
               self.p2 * part_y_min / part_y_max +
               self.p3 * part_w_min / part_w_max +
               self.p4 * part_h_min / part_h_max)
        return res

    def obtain_structure_similarity(self, structure1, structure2):
        layer1 = self.get_structure_layer(structure1)
        layer2 = self.get_structure_layer(structure2)
        max_layer = max(layer1, layer2)

        view_num1 = self.get_view_num(structure1)
        view_num2 = self.get_view_num(structure2)
        max_num = max(view_num1, view_num2)
        same_num = self.reckon_view_tree_similarity(structure1, structure2)

        part1 = min(layer1, layer2) / max_layer * 0.2
        part2 = min(view_num1, view_num2) / max_num * 0.2
        part3 = same_num / (view_num1 + view_num2 - same_num) * 0.6
        res = part1 + part2 + part3
        return res

    def reckon_view_tree_similarity(self, view_infos1, view_infos2):
        w = self.viewInfoThreshold
        res = 0
        if len(view_infos1) == 0:
            return res
        for view_info in view_infos1:
            matched_view_info_list = self.search_matched_view_info(view_info, view_infos2)
            if matched_view_info_list is None:
                continue
            max_num = 0
            for match_view_info in matched_view_info_list:
                similarity = self.obtain_view_similarity(view_info, match_view_info)
                temp = 0
                if similarity >= w:
                    temp = 1
                temp += self.reckon_view_tree_similarity(view_info.childs, match_view_info.childs)
                max_num = max(max_num, temp)
            res += max_num
        return res

    def search_matched_view_info(self, child_view_info, childs):
        if len(childs) == 0:
            return None
        matched_list = []
        for view_info in childs:
            if view_info.class_name == child_view_info.class_name and view_info.view_index == child_view_info.view_index:
                matched_list.append(view_info)
        return matched_list

    def get_view_num(self, structure):
        queue = list(structure)
        num = 0
        while queue:
            view_info = queue.pop(0)
            num += 1
            child_view_infos = view_info.childs
            if len(child_view_infos) != 0:
                queue.extend(child_view_infos)
        return num

    def get_structure_layer(self, structure):
        res = 0
        for view_info in structure:
            res = max(res, self.get_view_tree_layer(view_info))
        return res

    def get_view_tree_layer(self, view_info):
        if len(view_info.childs) == 0:
            return 1
        res = 1
        childs = view_info.childs
        for child in childs:
            res = max(res, self.get_view_tree_layer(child) + 1)
        return res

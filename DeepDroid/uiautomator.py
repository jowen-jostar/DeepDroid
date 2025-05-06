from copy import deepcopy
import xmltodict
import time
import DeepDroid.DataBase as db
import random
import subprocess
import os
from collections import deque
import cv2


def check_two_page_same(pre_xml_path, xml_path):
    pre_node_queue = deque()
    node_queue = deque()

    with open(pre_xml_path, 'r', encoding="utf-8") as f:
        xml_dict = xmltodict.parse(f.read())
    if "node" in xml_dict["hierarchy"].keys():
        if isinstance(xml_dict["hierarchy"]["node"], list):
            for sub_node in reversed(xml_dict["hierarchy"]["node"]):
                if 'com.android.systemui' not in sub_node['@resource-id'] and 'com.android.systemui' not in sub_node['@package']:
                    pre_node_queue.append(sub_node)
        else:
            if 'com.android.systemui' not in xml_dict["hierarchy"]["node"]['@resource-id'] and 'com.android.systemui' not in xml_dict["hierarchy"]["node"]['@package']:
                pre_node_queue.append(xml_dict["hierarchy"]["node"])

    with open(xml_path, 'r', encoding="utf-8") as f:
        xml_dict = xmltodict.parse(f.read())
    if "node" in xml_dict["hierarchy"].keys():
        if isinstance(xml_dict["hierarchy"]["node"], list):
            for sub_node in reversed(xml_dict["hierarchy"]["node"]):
                if 'com.android.systemui' not in sub_node['@resource-id'] and 'com.android.systemui' not in sub_node['@package']:
                    node_queue.append(sub_node)
        else:
            if 'com.android.systemui' not in xml_dict["hierarchy"]["node"]['@resource-id'] and 'com.android.systemui' not in xml_dict["hierarchy"]["node"]['@package']:
                node_queue.append(xml_dict["hierarchy"]["node"])

    return pre_node_queue == node_queue


def handle_none_action():
    print("当前页面无可执行动作，返回上一页面")
    db.device.press("back")
    time.sleep(2)
    check_out_of_app()


def check_out_of_app():
    package_name, activity_name = get_avd_running_app_status()
    if package_name != db.AUT:
        print("动作执行后进入了其他app，执行系统返回")
        db.device.press("back")
        time.sleep(2)
        package_name, activity_name = get_avd_running_app_status()
        if package_name != db.AUT:
            start_app(db.AUT)


def screen_shot(index: int, action, save_path):
    bounds = get_view_bounds(action)
    cmd = r"adb shell /system/bin/screencap -p /sdcard/screenshot-" + str(index) + ".png"
    os.system(cmd)
    cmd = r"adb pull /sdcard/screenshot-" + str(index) + ".png " + save_path
    os.system(cmd)
    image = cv2.imread(save_path + "screenshot-" + str(index) + ".png")
    if image is not None:
        cv2.rectangle(image, (bounds[0][0], bounds[0][1]), (bounds[1][0], bounds[1][1]), (0, 0, 255), 4)
        cv2.imwrite(save_path + "screenshot-" + str(index) + ".png", image)


def get_avd_running_app_status():
    device_id = db.AVD_SERIAL
    adb_path = "adb"  # 确保adb已经添加到系统环境变量中，或者提供adb的完整路径
    device_arg = f"-s {device_id}"
    output = subprocess.check_output([adb_path, "shell", "dumpsys", "activity", "activities", device_arg]).decode("utf-8")
    lines = output.split("\n")
    for line in lines:
        if "mResumedActivity" in line:
            activity_line = line.strip()
            break

    activity_parts = activity_line.split(" ")
    package_name = activity_parts[3].split("/")[0][:]
    activity_name = activity_parts[3].split("/")[1][1:]

    return package_name, activity_name


# 开启被测应用（AUT）
def start_app(package):
    # 启动app
    db.device.app_start(package)
    time.sleep(8)


# 关闭被测应用（AUT）
def stop_app(package):
    # 停止app
    db.device.app_stop(package)
    time.sleep(2)


def get_page_texts(xml_path):
    # 返回页面所有文本
    page_texts = ""
    node_queue = deque()
    package = db.AUT

    with open(xml_path, 'r', encoding="utf-8") as f:
        xml_dict = xmltodict.parse(f.read())

    if "node" in xml_dict["hierarchy"].keys():
        if isinstance(xml_dict["hierarchy"]["node"], list):
            for sub_node in reversed(xml_dict["hierarchy"]["node"]):
                if 'com.android.systemui' not in sub_node['@resource-id'] and 'com.android.systemui' not in sub_node['@package']:
                    node_queue.append(sub_node)
        else:
            if 'com.android.systemui' not in xml_dict["hierarchy"]["node"]['@resource-id'] and 'com.android.systemui' not in xml_dict["hierarchy"]["node"]['@package']:
                node_queue.append(xml_dict["hierarchy"]["node"])

    while len(node_queue) != 0:
        node = node_queue.pop()
        if 'com.android.systemui' in node['@resource-id'] or 'com.android.systemui' in node['@package']:
            continue

        if node['@package'] == package and node['@enabled'] == 'true' and node['@visible-to-user'] == 'true' and node['@text'] != "":
            if page_texts != "":
                page_texts += ", "
            newline_index = node['@text'].find('\n')
            if newline_index != -1:  # 若有多行文字，只取第一行
                node['@text'] = node['@text'][:newline_index]
            if len(node['@text']) > db.max_character:  # 若字符过多，则截取
                node['@text'] = node['@text'][:db.max_character].strip() + "..."
            page_texts = page_texts + "'" + node['@text'] + "'"
        if "node" in node.keys():
            if isinstance(node["node"], list):
                for sub_node in reversed(node["node"]):
                    node_queue.append(sub_node)
            else:
                node_queue.append(node["node"])

    package_name, activity_name = get_avd_running_app_status()
    page_texts = "Current function GUI page is " + activity_name.split('.')[-1].replace('Activity', '') + ", which has the following texts: " + page_texts + "."
    return page_texts


def analysis_state(xml_path):
    structure_now = db.structure_creator.get_structure_from_xml(xml_path)
    similarity = -100
    for state in db.states.keys():
        if state.startswith(db.AUT):
            structure_state = db.states[state]
            sim = db.page_match.obtain_structure_similarity(structure_now, structure_state)
            if sim > similarity:
                similarity = sim
                sim_state = state

    if similarity > 0.6:
        sim_page = sim_state.split(".")[-1]
    else:
        sim_page = "Unknown"

    # 返回所有可操作部件
    actions = []
    node_queue = deque()
    package = db.AUT

    with open(xml_path, 'r', encoding="utf-8") as f:
        xml_dict = xmltodict.parse(f.read())

    if "node" in xml_dict["hierarchy"].keys():
        if isinstance(xml_dict["hierarchy"]["node"], list):
            for sub_node in reversed(xml_dict["hierarchy"]["node"]):
                if 'com.android.systemui' not in sub_node['@resource-id'] and 'com.android.systemui' not in sub_node['@package']:
                    node_queue.append(sub_node)
        else:
            if 'com.android.systemui' not in xml_dict["hierarchy"]["node"]['@resource-id'] and 'com.android.systemui' not in xml_dict["hierarchy"]["node"]['@package']:
                node_queue.append(xml_dict["hierarchy"]["node"])

    while len(node_queue) != 0:
        node = node_queue.pop()
        if 'com.android.systemui' in node['@resource-id'] or 'com.android.systemui' in node['@package']:
            continue
        if "node" not in node.keys():
            continue

        if isinstance(node["node"], list):
            for sub_node in node["node"]:
                if sub_node['@package'] == package and sub_node['@enabled'] == 'true' and sub_node['@visible-to-user'] == 'true':
                    # 可点击事件和文本输入
                    analysis_click(sub_node, actions, node, sim_page)
                    # 可长点击事件
                    analysis_long_click(sub_node, actions, node, sim_page)
                    # 可滚动事件
                    analysis_scroll(sub_node, actions, node, sim_page)
                    # 可滑动（滑块）
                    analysis_slider(sub_node, actions, node, sim_page)
        elif node["node"]['@package'] == package and node["node"]['@enabled'] == 'true' and node["node"]['@visible-to-user'] == 'true':
            # 可点击事件和文本输入
            analysis_click(node["node"], actions, node, sim_page)
            # 可长点击事件
            analysis_long_click(node["node"], actions, node, sim_page)
            # 可滚动事件
            analysis_scroll(node["node"], actions, node, sim_page)
            # 可滑动（滑块）
            analysis_slider(node["node"], actions, node, sim_page)

        if isinstance(node["node"], list):
            for sub_node in reversed(node["node"]):
                node_queue.append(sub_node)
        else:
            node_queue.append(node["node"])

    return actions


def set_event(action, node, pnode, sim_page):
    child_nodes = ""
    node_queue = deque()
    resources = []
    if "node" in node.keys():
        if isinstance(node["node"], list):
            for sub_node in reversed(node["node"]):
                node_queue.append(sub_node)
        else:
            node_queue.append(node["node"])

    while len(node_queue) != 0:
        sub_node = node_queue.pop()
        if (sub_node['@package'] == node['@package'] and sub_node['@visible-to-user'] == 'true' and
                (sub_node['@clickable'] == 'true' or
                 (sub_node['@long-clickable'] == 'true' and 'EditText' not in sub_node['@class']) or
                 (sub_node['@scrollable'] == 'true' and 'Spinner' not in sub_node['@class']) or
                 ('SeekBar' in sub_node['@class'] and sub_node['@clickable'] == 'false'))):
            continue

        resource_str = sub_node["@resource-id"]
        id_index = resource_str.find(":id/")  # 查找":id/"的位置
        if id_index != -1:  # 找到":id/"
            resource_str = resource_str[id_index + len(":id/"):]  # 截取 ":id/" 之后的字符串

        newline_index = sub_node['@text'].find('\n')
        if newline_index != -1:  # 若有多行文字，只取第一行
            sub_node['@text'] = sub_node['@text'][:newline_index]
        if len(sub_node['@text']) > db.max_character:  # 若字符过多，则截取
            sub_node['@text'] = sub_node['@text'][:db.max_character].strip() + "..."

        if resource_str != "" and sub_node["@text"] != "":
            r_t_str = resource_str + "/" + sub_node["@text"]
            if r_t_str not in resources:
                resources.append(r_t_str)
        elif sub_node["@text"] != "":
            r_t_str = sub_node["@text"]
            if r_t_str not in resources:
                resources.append(r_t_str)
        else:
            if resource_str != "":
                r_t_str = resource_str
                if r_t_str not in resources:
                    resources.append(r_t_str)
            if "node" in sub_node.keys():
                if isinstance(sub_node["node"], list):
                    for sub_sub_node in reversed(sub_node["node"]):
                        node_queue.append(sub_sub_node)
                else:
                    node_queue.append(sub_node["node"])

    for i in range(len(resources)):
        if i == 0:
            child_nodes = resources[i]
        else:
            child_nodes = child_nodes + ", " + resources[i]

    parent_node = ""
    resource_str = pnode["@resource-id"]
    id_index = resource_str.find(":id/")  # 查找":id/"的位置
    if id_index != -1:  # 找到":id/"
        resource_str = resource_str[id_index + len(":id/"):]  # 截取 ":id/" 之后的字符串
    newline_index = pnode['@text'].find('\n')
    if newline_index != -1:  # 若有多行文字，只取第一行
        pnode['@text'] = pnode['@text'][:newline_index]
    if len(pnode['@text']) > db.max_character:  # 若字符过多，则截取
        pnode['@text'] = pnode['@text'][:db.max_character].strip() + "..."
    if resource_str == "":
        parent_node = pnode["@text"]
    else:
        parent_node = resource_str
        if pnode["@text"] != "":
            parent_node = parent_node + "/" + pnode["@text"]

    sibling_nodes = ""
    if isinstance(pnode["node"], list):
        resources = []
        for sub_node in pnode["node"]:
            if sub_node == node:
                continue
            resource_str = sub_node["@resource-id"]
            id_index = resource_str.find(":id/")  # 查找":id/"的位置
            if id_index != -1:  # 找到":id/"
                resource_str = resource_str[id_index + len(":id/"):]  # 截取 ":id/" 之后的字符串
            newline_index = sub_node['@text'].find('\n')
            if newline_index != -1:  # 若有多行文字，只取第一行
                sub_node['@text'] = sub_node['@text'][:newline_index]
            if len(sub_node['@text']) > db.max_character:  # 若字符过多，则截取
                sub_node['@text'] = sub_node['@text'][:db.max_character].strip() + "..."
            if resource_str != "" and sub_node["@text"] != "":
                r_t_str = resource_str + "/" + sub_node["@text"]
                if r_t_str not in resources:
                    resources.append(r_t_str)
            elif resource_str != "":
                r_t_str = resource_str
                if r_t_str not in resources:
                    resources.append(r_t_str)
            elif sub_node["@text"] != "":
                r_t_str = sub_node["@text"]
                if r_t_str not in resources:
                    resources.append(r_t_str)
        for i in range(len(resources)):
            if i == 0:
                sibling_nodes = resources[i]
            else:
                sibling_nodes = sibling_nodes + ", " + resources[i]

    a = {
        "page_name": sim_page,
        "action": action,
        "index": node["@index"],
        "text": node["@text"],
        "resource-id": node["@resource-id"],
        "class": node["@class"],
        "package": node["@package"],
        "content-desc": node["@content-desc"],
        "checkable": node["@checkable"],
        "checked": node["@checked"],
        "clickable": node["@clickable"],
        "enabled": node["@enabled"],
        "focusable": node["@focusable"],
        "focused": node["@focused"],
        "scrollable": node["@scrollable"],
        "long-clickable": node["@long-clickable"],
        "password": node["@password"],
        "selected": node["@selected"],
        "visible-to-user": node["@visible-to-user"],
        "bounds": node["@bounds"],
        "parent_node": parent_node,
        "sibling_nodes": sibling_nodes,
        "child_nodes": child_nodes
    }
    return deepcopy(a)


def analysis_click(node, actions, pnode, sim_page):
    if node['@clickable'] == 'true':
        if 'EditText' not in node['@class'] and 'AutoCompleteTextView' not in node['@class']:  # 普通的按钮点击
            event = set_event("click", node, pnode, sim_page)
            actions.append(dict(**event))
        else:  # 文本输入框
            event = set_event("text", node, pnode, sim_page)
            actions.append(dict(**event))


def analysis_long_click(node, actions, pnode, sim_page):
    if node['@long-clickable'] == 'true' and 'EditText' not in node['@class']:
        # 该控件可长点击，添加可执行事件
        event = set_event("long-click", node, pnode, sim_page)
        actions.append(dict(**event))


def analysis_scroll(node, actions, pnode, sim_page):
    if node['@scrollable'] == 'true' and 'Spinner' not in node['@class']:
        # 该控件可滚动，添加可执行事件
        event = set_event("swipe", node, pnode, sim_page)
        actions.append(dict(**event))


def analysis_slider(node, actions, pnode, sim_page):
    # 该控件可滑动，添加可执行事件
    if 'SeekBar' in node['@class'] and node['@clickable'] == 'false':
        event = set_event("slider", node, pnode, sim_page)
        actions.append(dict(**event))


# 转储页面结构
def dump_page():
    xml = db.device.dump_hierarchy()
    package_name, activity_name = get_avd_running_app_status()
    avd_running_app_status = package_name + '.' + activity_name

    # 保存页面结构到文件中
    page_path = './test_record/' + db.test_name + '/page/'
    if not os.path.exists(page_path):
        os.makedirs(page_path)
    files = os.listdir(page_path)
    filename = page_path + str(len(files)) + '_' + avd_running_app_status + '.xml'
    with open(filename, 'w', encoding="utf-8") as f:
        f.write(xml)
    f.close()

    return filename


def dump_page_fr():
    xml = db.device.dump_hierarchy()
    package_name, activity_name = get_avd_running_app_status()
    avd_running_app_status = package_name + '.' + activity_name

    # 保存页面结构到文件中
    page_path = './test_record/' + db.app.replace(" ", "") + '_' + db.test_name + '/page/'
    if not os.path.exists(page_path):
        os.makedirs(page_path)
    files = os.listdir(page_path)
    filename = page_path + str(len(files)) + '_' + avd_running_app_status + '.xml'
    with open(filename, 'w', encoding="utf-8") as f:
        f.write(xml)
    f.close()

    return filename


def execute_action(action, input_str):
    action_type = action["action"]
    if action_type == "click":
        x, y = get_view_position(action)
        db.device.click(x, y)
        combine_text = action['text'] + " " + action['resource-id'] + " " + action['parent_node'] + " " + action['child_nodes']
        if "sign_in_btn" in combine_text or "sign_in_fragment_sign_in_button" in combine_text or "Sign-In" in combine_text or "login_login" in combine_text or "Sign in" in combine_text:
            time.sleep(8)  # 等待登录完成
    elif action_type == "text":
        combine_text = action['text'] + " " + action['resource-id'] + " " + action['parent_node'] + " " + action['child_nodes']
        if "email" in combine_text.lower() or "e-mail" in combine_text.lower():
            input_str = db.email
        elif "password" in combine_text.lower():
            input_str = db.password
        # 先判断对应的UI对象是否获取存在
        if db.device(resourceId=action['resource-id']).exists:
            db.device(resourceId=action['resource-id']).send_keys(input_str)
            time.sleep(2)
            if input_str == db.password:
                db.device.click(993, 1270)
            else:
                db.device.click(988, 1935)
        else:
            # 搜索不到对应的UI对象，执行个系统事件（音量键）
            db.device.press("volume_up")
    elif action_type == "long-click":
        x, y = get_view_position(action)
        long_click_time = 1
        db.device.long_click(x, y, long_click_time)
    elif action_type == "swipe":
        length = 16
        if db.device(resourceId=action['resource-id'], className=action['class'], index=action['index']).exists:  # 纵向滑动
            db.device(resourceId=action['resource-id'], className=action['class'], index=action['index']).swipe("up", length)
        elif db.device(className=action['class'], index=action['index']).exists:  # 纵向滑动
            db.device(className=action['class'], index=action['index']).swipe("up", length)
        else:
            # 控件未找到，执行系统事件：调音量键
            db.device.press("volume_up")
    elif action_type == "slider":
        length = 16
        if db.device(resourceId=action['resource-id'], className=action['class'], index=action['index']).exists:  # 横向滑动
            if random.random() > 0.5:
                db.device(resourceId=action['resource-id'], className=action['class'], index=action['index']).swipe("right", length)
            else:
                db.device(resourceId=action['resource-id'], className=action['class'], index=action['index']).swipe("left", length)
        elif db.device(className=action['class'], index=action['index']).exists:  # 横向滑动
            if random.random() > 0.5:
                db.device(className=action['class'], index=action['index']).swipe("right", length)
            else:
                db.device(className=action['class'], index=action['index']).swipe("left", length)
        else:
            # 控件未找到，执行系统事件：调音量键
            db.device.press("volume_down")
    else:
        print("动作无效")
    time.sleep(5)


# 分析bounds
def get_view_bounds(action):
    temp = action['bounds']
    for i in range(len(temp)):
        if temp[i] == ']':
            temp = temp[0:i + 1] + "," + temp[i + 1:]
            break
    pos = eval(temp)
    return pos


# 定位控件
def get_view_position(action):
    pos = get_view_bounds(action)
    x = (pos[0][0] + pos[1][0]) / 2
    y = (pos[0][1] + pos[1][1]) / 2
    return x, y

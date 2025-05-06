import json
from copy import deepcopy
import xmltodict
import re
import time
import DeepDroid.PreExplore.DateBasePE as db
import random
import DeepDroid.PreExplore.LLMPE as LLM
import shutil
from DeepDroid.PreExplore.page_match import CustomEncoder


# 开启被测应用（AUT）
def start_app(package):
    db.path = []
    # 启动app
    db.device.app_start(package)
    time.sleep(8)


# 关闭被测应用（AUT）
def stop_app(package):
    # 停止app
    db.device.app_stop(package)


def refresh_path(state):
    path = db.path
    state_name = re.sub(r'\d+$', '', state.split('.')[-1])
    while state_name in path:
        path.pop()
    path.append(state_name)
    db.path = path


def get_state():
    # 转储页面结构
    xml = db.device.dump_hierarchy()
    # 保存页面结构到文件中/字典中
    filename = './pages/.xml'
    with open(filename, 'w', encoding="utf-8") as f:
        f.write(xml)
    f.close()

    similarity = -100
    structure_now = db.structure_creator.get_structure_from_xml(filename)
    for state in db.states.keys():
        if state.startswith(db.AUT):
            structure_state = db.states[state]
            sim = db.page_match.obtain_structure_similarity(structure_now, structure_state)
            if sim > similarity:
                similarity = sim
                sim_state = state

    if similarity > 0.9:
        state_now = sim_state
        refresh_path(state_now)
    else:
        state_now = LLM.get_state_name()
        shutil.copyfile(filename, './pages/' + state_now + '.xml')
        db.states[state_now] = structure_now
        with open('./states.json', 'w', encoding='utf-8') as file:
            json.dump(db.states, file, cls=CustomEncoder, indent=4)

        refresh_path(state_now)
        db.state_path[state_now] = deepcopy(db.path)
        with open('./state_path.json', 'w', encoding='utf-8') as file:
            json.dump(db.state_path, file, indent=4)

    analysis_action(state_now)
    return state_now


# 分析界面层次结构，生成可执行动作
def analysis_action(observation):
    # 保存当前状态下的各类型可执行事件,每次的新界面需要清空
    print("     >>>开始分析界面动作.......")
    db.current_event = []

    filename = './pages/' + observation + '.xml'
    # 分析页面结构，获取可执行事件1
    with open(filename, 'r', encoding="utf-8") as f:
        line = f.readline()  # 调用文件的 readline()方法
        while line:
            # 处理页面结构，每一个node读取一次
            if re.match('<node ', line.strip()) is not None:
                # 规范化每一个节点标签，去除前后的空格，去掉/，添加</node>
                new_line = list(line.strip())
                if new_line[len(new_line) - 2] == '/':
                    new_line[len(new_line) - 2] = ''
                line = ''.join(new_line) + "</node>"
                # 每一个node转成一个字典对象,当前的标签节点
                node_dict = xmltodict.parse(line)
                node = node_dict['node']
                # 分析页面节点属性，主要包括可点击，可长点击，可滚动，以及文本输入（待思考处理方式）
                if node['@package'] == db.AUT and node['@enabled'] == 'true' and node['@visible-to-user'] == 'true':
                    # 可点击事件和文本输入
                    analysis_click(node)
                    # 可长点击事件
                    analysis_long_click(node)
                    # 可滚动事件
                    # analysis_scroll(node)
                    # 可滑动（滑块）
                    analysis_slider(node)
            line = f.readline()
        print("     动作数目", len(db.current_event))
    f.close()


def set_event(x, y, input_str, direction, direction_len, long_click_time, id, cls, text, index):
    a = {'@x': x, '@y': y, '@input': input_str, '@direction': direction, '@direction_len': direction_len,
         '@long_click_time': long_click_time, '@id': id, '@class': cls, '@text': text, '@index': index}
    return deepcopy(a)


def get_x_y(node):
    pos = get_view_bounds(node)
    x = (pos[1][0] + pos[0][0]) / 2
    y = (pos[1][1] + pos[0][1]) / 2
    return x, y


def analysis_click(node):
    if node['@clickable'] == 'true':
        if 'EditText' not in node['@class']:  # 普通的按钮点击
            x, y = get_x_y(node)
            a = set_event(x, y, "", "", 0, 0, node['@resource-id'], node['@class'], node['@text'], node['@index'])
            event = {}
            act = [a]
            event['type'] = 'click'
            event['act'] = act[:]
            db.current_event.append(dict(**event))
        else:  # 文本输入框
            # 随机生成一个输入,或者从字符串池中选取字符串
            input_str = "London"
            x, y = get_x_y(node)
            a = set_event(x, y, input_str, "", 0, 0, node['@resource-id'], node['@class'], node['@text'], node['@index'])
            event_1 = {}
            act_1 = [a]
            event_1['type'] = 'edit'
            event_1['act'] = act_1[:]
            db.current_event.append(dict(**event_1))


def analysis_long_click(node):
    if node['@long-clickable'] == 'true' and 'EditText' not in node['@class']:
        # 该控件可长点击，添加可执行事件
        x, y = get_x_y(node)
        a = set_event(x, y, "", "", 0, 1, node['@resource-id'], node['@class'], node['@text'], node['@index'])
        event = {}
        act = [a]
        event['type'] = 'long-click'
        event['act'] = act[:]
        db.current_event.append(dict(**event))


def analysis_scroll(node):
    if node['@scrollable'] == 'true' and 'Spinner' not in node['@class']:
        # 该控件可滚动，添加可执行事件
        x, y = get_x_y(node)
        # 滚动方向
        direction = 'y'
        # 滚动距离，后期可以采用获取屏幕高度
        direction_len = 16
        a = set_event(x, y, "", direction, direction_len, 0, node['@resource-id'], node['@class'], node['@text'], node['@index'])
        event = {}
        act = [a]
        event['type'] = 'scrollable'
        event['act'] = act[:]
        db.current_event.append(dict(**event))


def analysis_slider(node):
    # 该控件可滑动，添加可执行事件
    if 'SeekBar' in node['@class'] and node['@clickable'] == 'false':
        x, y = get_x_y(node)
        # 滑动方向
        direction = 'x'
        # 滑动距离，后期可以采用获取屏幕高度
        direction_len = 16
        a = set_event(x, y, "", direction, direction_len, 0, node['@resource-id'], node['@class'], node['@text'], node['@index'])
        event = {}
        act = [a]
        event['type'] = 'slider'
        event['act'] = act[:]
        db.current_event.append(dict(**event))


def get_cur_action(action_index):
    action = db.current_event[action_index]
    action_type = action['type']
    return action, action_type


def excute_action(action, action_type):
    if action_type == "click":
        x = action['act'][0]['@x']
        y = action['act'][0]['@y']
        db.device.click(x, y)
    elif action_type == "edit":
        input_str = action['act'][0]['@input']
        # 先判断对应的UI对象是否获取存在
        if db.device(resourceId=action['act'][0]['@id']).exists:
            db.device(resourceId=action['act'][0]['@id']).send_keys(input_str)
        else:
            # 搜索不到对应的UI对象，执行个系统事件（音量键）
            db.device.press("volume_up")
    elif action_type == "long-click":
        x = action['act'][0]['@x']
        y = action['act'][0]['@y']
        long_click_time = action['act'][0]['@long_click_time']
        db.device.long_click(x, y, long_click_time)
    elif action_type == "scrollable":
        x = action['act'][0]['@x']
        y = action['act'][0]['@y']
        length = action['act'][0]['@direction_len']
        if db.device(resourceId=action['act'][0]['@id'], className=action['act'][0]['@class'], index=action['act'][0]['@index']).exists:
            if action['act'][0]['@direction'] == 'x':  # 横向滑动
                db.device(resourceId=action['act'][0]['@id'], className=action['act'][0]['@class'], index=action['act'][0]['@index']).swipe("left", length)
            else:  # 纵向滑动
                db.device(resourceId=action['act'][0]['@id'], className=action['act'][0]['@class'], index=action['act'][0]['@index']).swipe("up", length)
        elif db.device(className=action['act'][0]['@class'], index=action['act'][0]['@index']).exists:
            if action['act'][0]['@direction'] == 'x':  # 横向滑动
                db.device(className=action['act'][0]['@class'], index=action['act'][0]['@index']).swipe("left", length)
            else:  # 纵向滑动
                db.device(className=action['act'][0]['@class'], index=action['act'][0]['@index']).swipe("up", length)
        else:
            # 控件未找到，执行系统事件：调音量键
            db.device.press("volume_up")
    elif action_type == "slider":
        x = action['act'][0]['@x']
        y = action['act'][0]['@y']
        length = action['act'][0]['@direction_len']
        if db.device(resourceId=action['act'][0]['@id'], className=action['act'][0]['@class'], index=action['act'][0]['@index']).exists:
            if action['act'][0]['@direction'] == 'x':  # 横向滑动
                if random.random() > 0.5:
                    db.device(resourceId=action['act'][0]['@id'], className=action['act'][0]['@class'], index=action['act'][0]['@index']).swipe("right", length)
                else:
                    db.device(resourceId=action['act'][0]['@id'], className=action['act'][0]['@class'], index=action['act'][0]['@index']).swipe("left", length)
            else:  # 纵向滑动
                db.device(resourceId=action['act'][0]['@id'], className=action['act'][0]['@class'], index=action['act'][0]['@index']).swipe("up", length/2)
        elif db.device(className=action['act'][0]['@class'], index=action['act'][0]['@index']).exists:
            if action['act'][0]['@direction'] == 'x':  # 横向滑动
                if random.random() > 0.5:
                    db.device(className=action['act'][0]['@class'], index=action['act'][0]['@index']).swipe("right", length)
                else:
                    db.device(className=action['act'][0]['@class'], index=action['act'][0]['@index']).swipe("left", length)
            else:  # 纵向滑动
                db.device(className=action['act'][0]['@class'], index=action['act'][0]['@index']).swipe("up", length/2)
        else:
            # 控件未找到，执行系统事件：调音量键
            db.device.press("volume_down")
    else:
        print("动作无效")
    time.sleep(5)


# 分析bounds
def get_view_bounds(node):
    temp = node['@bounds']
    for i in range(len(temp)):
        if temp[i] == ']':
            temp = temp[0:i + 1] + "," + temp[i + 1:]
            break
    pos = eval(temp)
    return pos


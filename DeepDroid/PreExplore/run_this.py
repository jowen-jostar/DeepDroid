import json
import os
import random
import DeepDroid.PreExplore.uiautomatorPE as ui
import time
import DeepDroid.PreExplore.DateBasePE as db
import DeepDroid.DataBase as DataBase
import csv
from DeepDroid.PreExplore.page_match import custom_decoder


def explore():
    for _ in range(db.max_step):
        # 获取环境初始状态，observations是状态id
        observation = ui.get_state()
        if len(db.current_event) == 0:
            print("当前状态无可执行动作，返回上一状态")
            db.device.press("back")
            time.sleep(4)
            if db.device.app_current()['package'] != db.AUT:
                ui.start_app(db.AUT)
            observation = ui.get_state()
        print("当前状态：", observation)
        action_index = random.randint(0, len(db.current_event) - 1)
        action, action_type = ui.get_cur_action(action_index)
        print(">>>开始执行动作,类型：", action['type'], action['act'][0]['@id'], "class:", action['act'][0]['@class'])
        ui.excute_action(action, action_type)
        # 判断当前状态是否属于AUT
        if db.device.app_current()['package'] != db.AUT:
            # 当前状态不在被测应用中
            db.device.press("back")
            time.sleep(4)
            if db.device.app_current()['package'] != db.AUT:
                ui.start_app(db.AUT)


def test_one_app():
    # 连接设备,打开被测应用，即初始化环境
    ui.start_app(db.AUT)
    explore()
    ui.stop_app(db.AUT)


if __name__ == "__main__":
    # 加载已标注页面
    if os.path.exists('./states.json'):
        if os.path.getsize('./states.json'):
            print('states文件存在且不为空')
            with open("states.json", 'r', encoding='utf-8') as file:
                db.states = json.load(file, object_hook=custom_decoder)
        else:
            print('states文件存在且为空')
    else:
        print('states文件不存在')
        file = open("states.json", 'w', encoding='utf-8')
        file.close()
    # 加载已标注页面的路径
    if os.path.exists('./state_path.json'):
        if os.path.getsize('./state_path.json'):
            print('state_path文件存在且不为空')
            with open("./state_path.json", 'r', encoding='utf-8') as file:
                db.state_path = json.load(file)
        else:
            print('state_path文件存在且为空')
    else:
        print('state_path文件不存在')
        file = open("./state_path.json", 'w', encoding='utf-8')
        file.close()

    with open('./app_info.csv') as f:
        reader = csv.DictReader(f)
        for line in reader:
            db.app_function = line['app_function']
            db.AUT = line['AUT']
            DataBase.AUT = line['AUT']

            user_input = input("app: " + line['AUT'] + "    Please press Enter to start.")
            test_one_app()


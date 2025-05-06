import DeepDroid.LLM as LLM
import DeepDroid.PreExplore.DateBasePE as db
import DeepDroid.uiautomator as ui
import json
import os


def answer_cleansing(answer_LLM):
    try:
        start_index = answer_LLM.index('Page:')
        end_index = answer_LLM.index('Function:')
        state_name = answer_LLM[start_index + len('Page:'):end_index].strip()  # 获取匹配组中的文本
    except Exception as e:  # 捕获所有其他类型的异常
        print(f"Pattern 'Page:' unmatch: {str(e) + answer_LLM}")
        package_name, activity_name = ui.get_avd_running_app_status()
        state_name = activity_name.split('.')[-1].replace('Activity', '')

    try:
        start_index = answer_LLM.index('Function:')
        end_index = answer_LLM.rindex(')')
        functions_str = answer_LLM[start_index + len('Function:'):end_index].strip()  # 获取匹配组中的文本
        state_functions = functions_str.split(";")
        if state_functions[-1][-1] == '.':
            state_functions[-1] = state_functions[-1][:-1]
        for i in range(len(state_functions)):
            state_functions[i] = state_functions[i].strip()
    except Exception as e:  # 捕获所有其他类型的异常
        print(f"Pattern 'Function:' unmatch: {str(e) + answer_LLM}")
        functions_index = answer_LLM.find('Function:')
        if functions_index != -1:
            functions_str = answer_LLM[functions_index + len('Function:'):].strip()
            state_functions = functions_str.split(";")
            for i in range(len(state_functions)):
                state_functions[i] = state_functions[i].strip()
            state_functions = state_functions[:-1]
        else:
            state_functions = []
        print(len(state_functions))

    return state_name, state_functions


def get_state_name():
    xml_path = r'./pages/.xml'
    page_context = ui.get_page_texts(xml_path)
    actions = ui.analysis_state(xml_path)
    widget_context = LLM.get_widget_context(actions)
    prompt = (db.app_function + "\n" + page_context + "\n" + widget_context +
              "\nPlease describe this GUI page in a combination of words like MainLocationSelector or SettingDefaultLocation,"
              " and summarize its exclusive functions as few as possible with a few phrases separated by ';'."
              "\nPlease answer strictly in accordance with the following format: "
              "(Page: <Describe Word> Function: <Function Phrases>).")
    print(prompt)
    answer_LLM = LLM.decoder_for_deepseek(prompt, 128)
    state_name, state_functions = answer_cleansing(answer_LLM)

    app = db.device.app_current()['package']
    filename = 'functions.json'
    if not os.path.exists(filename):
        # 文件不存在，创建一个空的JSON文件
        file = open(filename, 'w', encoding='utf-8')
        file.close()
        functions = {}
    else:
        # 文件存在，读取文件内容
        with open(filename, 'r', encoding='utf-8') as file:
            functions = json.load(file)
    if app not in functions.keys():
        functions[app] = {}
    if state_name in functions[app].keys():
        # 重名，修改state_name
        count = 0
        for key_i in functions[app].keys():
            if key_i.startswith(state_name):
                count += 1
        state_name = state_name + str(count)
    functions[app][state_name] = state_functions
    # 将修改后的数据写回文件，实现信息覆盖
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(functions, file, indent=4)

    return db.AUT + '.' + state_name


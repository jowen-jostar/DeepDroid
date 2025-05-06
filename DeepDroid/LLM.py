from openai import OpenAI
import re
import DeepDroid.uiautomator as ui
import DeepDroid.DataBase as db
import json


def decoder_for_deepseek(input_str, max_length):
    api_key = db.api_key
    base_url = db.base_url
    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are an android application testing assistant"},
            {"role": "user", "content": input_str},
        ],
        stream=False,
        max_tokens=max_length,
        temperature=0,
        stop=None
    )

    return response.choices[0].message.content


def get_prompt(xml_path, actions, action_list):
    app_context = db.app_context
    target = db.target
    page_context = ui.get_page_texts(xml_path)
    widget_context = get_widget_context(actions)
    history_actions = get_history_actions(action_list)
    prompt = (app_context + "\n" + target + "\n" + history_actions + "\n" +
              page_context + "\n" + widget_context + "\nWhich widget id should I operate in this GUI page?\n"
              "Let's think step by step for one action and answer strictly in accordance with the following format: (Thought: <Reasoning> Action: <Widget Id> Input: <Input Text>).\n"
              "Note that <Widget Id> is -1 only when the entire task is complete, don't end the task when there are still steps, "
              "and don't do any extra operation after completing the task, such as going back to the home page, just output '-1'.\n"
              "Note that <Input Text> is required when the action you choose is 'text', and provide the words you want to enter.\n"
              "You can try swipe down this page or close this page to go back to the previous page and continue the task if you can't find the target widget.\n"
              "Note that the role of the previous step and the current page widgets is considered, and remember to check whether the target widget has already been operated in the previous steps.")
    return prompt


def get_same_page_prompt(prompt, pre_action):
    return (prompt + "\nNote that the last action " + get_action_str(pre_action) +
            " has been operated successfully, but the page didn't change. So you'd better not choose it anymore.")


def get_action_str(action):
    text_str = action["text"]
    newline_index = text_str.find('\n')
    if newline_index != -1:  # 若有多行文字，只取第一行
        text_str = text_str[:newline_index]
    if len(text_str) > db.max_character:  # 若字符过多，则截取
        text_str = text_str[:db.max_character].strip() + "..."

    resource_str = action["resource-id"]
    id_index = resource_str.find(":id/")  # 查找resource-id中 ":id/" 的位置
    if id_index != -1:  # 找到":id/"
        resource_str = resource_str[id_index + len(":id/"):]  # 截取resource-id中 ":id/" 之后的字符串

    return ("{'action': '" + action["action"] +
            "', 'text': '" + text_str +
            "', 'resource-id': '" + resource_str +
            "', 'class': '" + action["class"].split('.')[-1] +
            "', 'content-desc': '" + action["content-desc"] +
            "', 'parent_node': '" + action["parent_node"] +
            "', 'sibling_nodes': '" + action["sibling_nodes"] +
            "', 'child_nodes': '" + action["child_nodes"] + "'}")


def answer_cleansing(answer_LLM):  # return -1 if task is finished
    reasoning = answer_LLM
    action_num = -1
    input_str = ""

    pattern = r"Thought:(.*?)Action:"
    try:
        match = re.search(pattern, answer_LLM, re.DOTALL)
        reasoning = match.group(1).strip()  # 获取匹配组中的文本
    except Exception as e:  # 捕获所有其他类型的异常
        print(f"Pattern 'Thought:' unmatch: {str(e) + answer_LLM}")

    pattern = r"Action:(.*?)Input:"
    try:
        match = re.search(pattern, answer_LLM, re.DOTALL)
        action = match.group(1).strip()  # 获取匹配组中的文本
        numbers = re.findall(r'-?\d+', action)
        if numbers:
            action_num = int(numbers[-1])  # 返回最后一个匹配的数字
    except Exception as e:  # 捕获所有其他类型的异常
        print(f"Pattern 'Action:' unmatch: {str(e) + answer_LLM}")
        action_index = answer_LLM.find('Action:')
        if action_index != -1:
            action_str = answer_LLM[action_index + len('Action:'):].strip()
            numbers = re.findall(r'-?\d+', action_str)
            if numbers:
                action_num = int(numbers[0])  # 返回第一个匹配的数字
        else:
            numbers = re.findall(r'-?\d+', answer_LLM)
            if numbers:
                action_num = int(numbers[-1])  # 返回最后一个匹配的数字
        print(action_num)

    pattern = r"Input:(.*?)\)"
    try:
        match = re.search(pattern, answer_LLM, re.DOTALL)
        input_str = match.group(1).strip()  # 获取匹配组中的文本
    except Exception as e:  # 捕获所有其他类型的异常
        print(f"Pattern 'Input:' unmatch: {str(e) + answer_LLM}")
        input_index = answer_LLM.find('Input:')
        if input_index != -1:
            input_str = answer_LLM[input_index + len('Input:'):].strip()
        print(input_str)

    return reasoning, action_num, input_str


def get_app_context():
    if db.Manifest_xml != "":  # db.Manifest_xml在闭源应用里存储apk路径，apk路径存在
        app_context = db.function + "\nAll its main function pages are: " + db.activities + "."
    else:  # 闭源应用apk路径不存在
        app_context = db.function
    db.app_context = app_context


def get_target(target_file):
    filename = 'PreExplore/functions.json'
    with open(filename, 'r', encoding='utf-8') as file:
        functions = json.load(file)
    if db.AUT not in functions.keys():
        db.target = "I want to " + db.test + "."
    else:
        task = db.test
        tasks = []
        if "and" not in task.lower():
            tasks.append(task)
        else:
            prompt = """---Example---
Please break down the following task into as few independent tasks as possible: set London for favourites and set default location to London.
set London for favourites; set default location to London.
---End Example---

Please break down the following task into as few independent tasks as possible: """ + task + """.
Please answer in one sentence with independent tasks separated by ';'."""
            tasks = decoder_for_deepseek(prompt, 128).strip()
            subtasks = []
            if tasks[-1] == ";":
                tasks = tasks[:-1]
            tasks = tasks.split(";")
            if tasks[0][0].isupper():
                tasks[0] = tasks[0][0].lower() + tasks[0][1:]
            if tasks[-1][-1] == '.':
                tasks[-1] = tasks[-1][:-1]
            for i in range(len(tasks)):
                tasks[i] = tasks[i].strip()
                if tasks[i] != "":
                    subtasks.append(tasks[i])
            tasks = subtasks
        print(tasks)

        functions = functions[db.AUT]
        prompt = db.app_context + "\nI have explored the following pages and predicted its possible features:"
        for page in functions.keys():
            function = page + ": "
            for func in functions[page]:
                function = function + func + "; "
            prompt = prompt + "\n    " + function[:-2] + "."
        prompt = prompt + "\nPlease give me the page with the function that best matches the following tasks:"
        for i in range(len(tasks)):
            prompt = prompt + "\n    (" + str(i + 1) + ") " + tasks[i] + ";"
        if len(tasks) == 1:
            prompt = prompt[:-1] + (
                ".\nPlease answer with a page name corresponds strictly to the task."
                "\nNote that the page name should be selected from the name of the explored page mentioned above, "
                "and if there is no page that matches the corresponding task, select one of the function pages above to return."
                "\nNote that the page name should appear exactly as it appears above, and do not make any typos."
                "\nNote that you should output the page name only."
                "\nOutput example: MainLocation.")
        else:
            prompt = prompt[:-1] + (
                ".\nPlease answer with a sentence in which the order of the page names corresponds strictly to the order of the tasks, and the page names are separated by ';'."
                "\nNote that the page name should be selected from the name of the explored page mentioned above, "
                "and if there is no page that matches the corresponding task, select one of the function pages above to return."
                "\nNote that the page name should appear exactly as it appears above, and do not make any typos."
                "\nNote that you should output the page names only."
                "\nOutput example: MainLocation; MainSetting1.")
        print(prompt)
        pages = decoder_for_deepseek(prompt, 128).strip().split(";")
        if isinstance(pages, str):
            pages = [pages]
        if pages[-1][-1] == '.':
            pages[-1] = pages[-1][:-1]
        for i in range(len(pages)):
            colon_index = pages[i].rfind(":")
            if colon_index != -1:
                pages[i] = pages[i][colon_index + 1:]
            pages[i] = pages[i].strip()
        print(pages)

        target = "I want to " + db.test + ", in which "
        for i in range(len(tasks)):
            target = target + tasks[i] + " may be accomplished in " + pages[i] + " page, "
        target = target[:-2] + "."
        db.target = target
        print(target)

        with open(target_file, encoding="utf-8", mode="a") as file:
            file.write(str(tasks) + "\n\n" + prompt + "\n\n" + str(pages))


def get_widget_context(actions):
    if len(actions) == 0:
        page_name = "Unknown"
    else:
        page_name = actions[0]["page_name"]
    widget_context = "Current GUI page seems like " + page_name + " page, and it have the following widgets that can be operated:\n"
    for i in range(len(actions)):
        widget_context = widget_context + "    (Widget Id: " + str(i) + ") " + get_action_str(actions[i])
        if i == len(actions) - 1:
            widget_context += "."
        else:
            widget_context += ";\n"
    return widget_context


def get_history_actions(action_list):
    if len(action_list) == 0:
        history_actions = "This is the first action, and no action has been operated before."
    else:
        history_actions = "I have finished the following actions:\n"
        for i in range(len(action_list)):
            if action_list[i]["page_name"] != "Unknown":
                history_actions = history_actions + "    (Step " + str(i + 1) + " in " + action_list[i]["page_name"] + " page) " + get_action_str(action_list[i])
            else:
                history_actions = history_actions + "    (Step " + str(i + 1) + ") " + get_action_str(action_list[i])
            if i == len(action_list) - 1:
                history_actions += "."
            else:
                history_actions += ";\n"
    return history_actions


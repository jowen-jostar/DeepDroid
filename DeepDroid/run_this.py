import os
import DeepDroid.DataBase as db
import json
import DeepDroid.uiautomator as ui
import DeepDroid.LLM as LLM
import csv
from collections import deque
import xmltodict
from DeepDroid.PreExplore.page_match import custom_decoder


def get_answers():
    data_file = db.DataSet_DIR + db.test_name + "\\body.json"
    with open(data_file, 'r', encoding='utf-8') as file:
        answers = json.load(file)

    return answers


def get_success_num(answers, actions, xml_paths):
    answer_num = 0
    for i in range(len(actions)):
        if answers[answer_num]["action"] == "back":
            answers[answer_num]["action"] = "click"
        if check_success(answers[answer_num], actions[i], xml_paths[i]):
            answer_num += 1
        if answer_num == len(answers):
            break
    return answer_num


def get_success_num_consider_swipe(answers, actions, xml_paths):
    if len(answers) == 0:
        return 0

    max_answer_num = 0
    for i in range(len(actions)):
        if answers[max_answer_num]["action"] == "back":
            answers[max_answer_num]["action"] = "click"
        if check_success(answers[max_answer_num], actions[i], xml_paths[i]):
            max_answer_num += 1
        if max_answer_num == len(answers):
            break

    for i in range(len(answers)):  # 考虑到不同设备页面大小不同，swipe次数可能不同，递归检查去除swipe后answer_num是否增加
        if answers[i]["action"] == "swipe":
            sub_answer = answers[:i] + answers[i+1:]
            answer_num = get_success_num_consider_swipe(sub_answer, actions, xml_paths)
            if answer_num >= i:
                answer_num += 1
            if answer_num > max_answer_num:
                max_answer_num = answer_num

    return max_answer_num


def check_success(answer, action, xml_path):
    if answer["action"] != action["action"]:
        return False
    if check_action(answer, action):
        return True

    node_queue = deque()

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

        if check_node_action(node, action):  # node为action节点
            node_queue.clear()
            if "node" in node.keys():
                if isinstance(node["node"], list):
                    for sub_node in reversed(node["node"]):
                        node_queue.append(sub_node)
                else:
                    node_queue.append(node["node"])

            while len(node_queue) != 0:
                node = node_queue.pop()
                if (node['@package'] == answer['package'] and node['@enabled'] == 'true' and node['@visible-to-user'] == 'true' and
                        (node['@clickable'] == 'true' or
                         (node['@long-clickable'] == 'true' and 'EditText' not in node['@class']) or
                         (node['@scrollable'] == 'true' and 'Spinner' not in node['@class']) or
                         ('SeekBar' in node['@class'] and node['@clickable'] == 'false'))):
                    continue
                if check_node_answer(node, answer):  # node为answer节点，即action节点内部有answer节点，部件选取正确
                    return True
                if "node" in node.keys():
                    if isinstance(node["node"], list):
                        for sub_node in reversed(node["node"]):
                            node_queue.append(sub_node)
                    else:
                        node_queue.append(node["node"])

            return False  # action节点内部无answer节点，部件选取错误

        if "node" in node.keys():
            if isinstance(node["node"], list):
                for sub_node in reversed(node["node"]):
                    node_queue.append(sub_node)
            else:
                node_queue.append(node["node"])

    return False  # 若从此处返回说明xml_path文件中无action节点，bug


def check_action(answer, action):
    a = {
        "action": answer["action"],
        "resource-id": answer["resource-id"],
        "class": answer["class"],
        "package": answer["package"],
        "content-desc": answer["content-desc"],
    }
    b = {
        "action": action["action"],
        "resource-id": action["resource-id"],
        "class": action["class"],
        "package": action["package"],
        "content-desc": action["content-desc"],
    }
    if b["content-desc"].startswith("Signed in as"):
        b["content-desc"] = "Sign in"
    return a == b


def check_node_action(node_xml, action):
    a = {
        "index": node_xml["@index"],
        "text": node_xml["@text"],
        "resource-id": node_xml["@resource-id"],
        "class": node_xml["@class"],
        "package": node_xml["@package"],
        "content-desc": node_xml["@content-desc"],
        "checkable": node_xml["@checkable"],
        "checked": node_xml["@checked"],
        "clickable": node_xml["@clickable"],
        "enabled": node_xml["@enabled"],
        "focusable": node_xml["@focusable"],
        "focused": node_xml["@focused"],
        "scrollable": node_xml["@scrollable"],
        "long-clickable": node_xml["@long-clickable"],
        "password": node_xml["@password"],
        "selected": node_xml["@selected"],
        "visible-to-user": node_xml["@visible-to-user"],
        "bounds": node_xml["@bounds"],
    }
    b = {
        "index": action["index"],
        "text": action["text"],
        "resource-id": action["resource-id"],
        "class": action["class"],
        "package": action["package"],
        "content-desc": action["content-desc"],
        "checkable": action["checkable"],
        "checked": action["checked"],
        "clickable": action["clickable"],
        "enabled": action["enabled"],
        "focusable": action["focusable"],
        "focused": action["focused"],
        "scrollable": action["scrollable"],
        "long-clickable": action["long-clickable"],
        "password": action["password"],
        "selected": action["selected"],
        "visible-to-user": action["visible-to-user"],
        "bounds": action["bounds"],
    }
    return a == b


def check_node_answer(node_xml, answer):
    a = {
        "resource-id": node_xml["@resource-id"],
        "class": node_xml["@class"],
        "package": node_xml["@package"],
        "content-desc": node_xml["@content-desc"],
        "checkable": node_xml["@checkable"],
        "checked": node_xml["@checked"],
        "clickable": node_xml["@clickable"],
        "enabled": node_xml["@enabled"],
        "focusable": node_xml["@focusable"],
        "focused": node_xml["@focused"],
        "scrollable": node_xml["@scrollable"],
        "long-clickable": node_xml["@long-clickable"],
        "password": node_xml["@password"],
        "selected": node_xml["@selected"],
        "visible-to-user": node_xml["@visible-to-user"],
    }
    b = {
        "resource-id": answer["resource-id"],
        "class": answer["class"],
        "package": answer["package"],
        "content-desc": answer["content-desc"],
        "checkable": answer["checkable"],
        "checked": answer["checked"],
        "clickable": answer["clickable"],
        "enabled": answer["enabled"],
        "focusable": answer["focusable"],
        "focused": answer["focused"],
        "scrollable": answer["scrollable"],
        "long-clickable": answer["long-clickable"],
        "password": answer["password"],
        "selected": answer["selected"],
        "visible-to-user": answer["visible-to-user"],
    }
    return a == b


def prompt_one_test():
    test_name = db.test_name
    log_file = "./test_record/" + test_name + "/log.txt"
    target_file = "./test_record/" + test_name + "/target.txt"
    prompt_dir = './test_record/' + test_name + '/prompt/'
    action_dir = './test_record/' + test_name + '/action/'
    os.makedirs(prompt_dir, exist_ok=True)  # 确保目录存在
    os.makedirs(action_dir, exist_ok=True)

    LLM.get_app_context()
    LLM.get_target(target_file)
    ui.start_app(db.AUT)

    finish_flag = False
    action_list = []
    xml_path_list = []
    while finish_flag is False:
        if len(xml_path_list) != 0:
            pre_xml_path = xml_path
        xml_path = ui.dump_page()
        actions = ui.analysis_state(xml_path)
        if len(actions) == 0:
            ui.handle_none_action()
            xml_path = ui.dump_page()
            actions = ui.analysis_state(xml_path)
        prompt = LLM.get_prompt(xml_path, actions, action_list)
        with open(prompt_dir + "prompt" + str(len(action_list)) + ".txt", 'w', encoding='utf-8') as file:
            file.write(prompt)
        with open(action_dir + "action" + str(len(action_list)) + ".json", 'w', encoding='utf-8') as file:
            json.dump(actions, file, ensure_ascii=False, indent=4)

        prompt = db.few_shot + prompt  # few_shot
        if len(xml_path_list) != 0 and ui.check_two_page_same(pre_xml_path, xml_path):
            prompt = LLM.get_same_page_prompt(prompt, action_LLM)
        answer_LLM = LLM.decoder_for_deepseek(prompt, 512)
        reasoning, action_num, input_str = LLM.answer_cleansing(answer_LLM)  # return -1 if task is finished
        if action_num == -1 or action_num >= len(actions):
            action_LLM = "None, the task is finished."
            finish_flag = True
        else:
            action_LLM = actions[action_num]

            if action_list.count(action_LLM) >= 3:
                reasoning = reasoning + "\nBut this action has repeated 3 times, End the Test."
                action_LLM = "None, the task is finished."
                finish_flag = True

            if not finish_flag:
                ui.screen_shot(len(action_list), action_LLM, action_dir)
                ui.execute_action(action_LLM, input_str)
                action_list.append(action_LLM)
                xml_path_list.append(xml_path)
                ui.check_out_of_app()

        with open(log_file, encoding="utf-8", mode="a") as file:
            file.write("----------------test" + str(len(action_list)-1) + "----------------\nprompt:\n" + prompt +
                       "\nanswer from LLM:\n" + answer_LLM + "\nreasoning from LLM:\n" + reasoning +
                       "\naction from LLM:\n" + str(action_LLM) + "\n\n\n")
    # ui.stop_app(db.AUT)

    answers = get_answers()
    for i in range(len(answers)):
        with open(log_file, encoding="utf-8", mode="a") as file:
            file.write("answer" + str(i) + ": " + str(answers[i]) + "\n")
    # success_num = get_success_num(answers, action_list, xml_path_list)
    success_num = get_success_num_consider_swipe(answers, action_list, xml_path_list)

    # record SR, ACP
    with open(log_file, encoding="utf-8", mode="a") as file:
        file.write("\n\nACP: " + str(success_num) + "/" + str(len(answers)) + "=" + str(success_num/len(answers)) +
                   "\nSUCCESS: " + str(success_num == len(answers)))

    return success_num, len(answers), len(action_list)


def prompt_all_test():
    all_log_file = "./test_record/log.txt"
    all_log_file_new = "./test_record/log_new.txt"
    all_success_num = 0
    all_answer_num = 0
    all_action_num = 0
    SR = 0
    test_num = 0
    with open('./test_info.csv') as f:
        reader = csv.DictReader(f)
        for line in reader:
            db.app = line['app']
            db.test_name = line['test_name']
            db.test = line['test']
            db.function = line['function']
            db.Manifest_xml = line['Manifest_xml']
            db.AUT = line['AUT']
            db.activities = line['activities']
            db.course = line['course']  # open: 开源应用, close: 闭源应用

            user_input = input("test " + line['test_name'] + ": " + line['test'] + ". Please press Enter to start.")
            success_num, answer_num, action_num = prompt_one_test()
            test_num += 1
            all_success_num += success_num
            all_answer_num += answer_num
            all_action_num += action_num
            if success_num == answer_num:
                SR += 1

            # record SR, ACP
            with open(all_log_file, encoding="utf-8", mode="a") as file:
                file.write(
                    db.test_name + ":\nACP: " + str(success_num) + "/" + str(answer_num) + "=" + str(success_num / answer_num) +
                    "\nSUCCESS: " + str(success_num == answer_num) + "\n\n")

            # record AR
            if action_num == 0:
                with open(all_log_file_new, encoding="utf-8", mode="a") as file:
                    file.write(
                        db.test_name + ":\nAR: " + str(success_num) + "/" + str(action_num) + "=0.0" +
                        "\nSUCCESS: " + str(success_num == answer_num) + "\n\n")
            else:
                with open(all_log_file_new, encoding="utf-8", mode="a") as file:
                    file.write(
                        db.test_name + ":\nAR: " + str(success_num) + "/" + str(action_num) + "=" + str(success_num / action_num) +
                        "\nSUCCESS: " + str(success_num == answer_num) + "\n\n")

        # record SR, ACP
        with open(all_log_file, encoding="utf-8", mode="a") as file:
            file.write(
                "\n\nACP: " + str(all_success_num) + "/" + str(all_answer_num) + "=" + str(all_success_num / all_answer_num) +
                "\n\nSR: " + str(SR) + "/" + str(test_num) + "=" + str(SR / test_num))
        # record AR
        with open(all_log_file_new, encoding="utf-8", mode="a") as file:
            file.write(
                "\n\nAR: " + str(all_success_num) + "/" + str(all_action_num) + "=" + str(all_success_num / all_action_num))


if __name__ == "__main__":
    with open("./PreExplore/states.json", 'r', encoding='utf-8') as file:
        db.states = json.load(file, object_hook=custom_decoder)
    prompt_all_test()



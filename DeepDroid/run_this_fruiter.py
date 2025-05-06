import os
import re
import DeepDroid.DataBase as db
import json
import DeepDroid.uiautomator as ui
import DeepDroid.LLM as LLM
import csv
from collections import deque
import xmltodict
from DeepDroid.PreExplore.page_match import custom_decoder


def get_answers():
    answer_paths = {
        "ABC News": r"D:\dataset\FrUITeR\TestAnalyzer\input\extracted_tests\news\abc.csv",
        "BBC News": r"D:\dataset\FrUITeR\TestAnalyzer\input\extracted_tests\news\bbcnews.csv",
        "BuzzFeed": r"D:\dataset\FrUITeR\TestAnalyzer\input\extracted_tests\news\buzzfeed.csv",
        "Fox News": r"D:\dataset\FrUITeR\TestAnalyzer\input\extracted_tests\news\fox.csv",
        "News Republic": r"D:\dataset\FrUITeR\TestAnalyzer\input\extracted_tests\news\newsrepublic.csv",
        "SmartNews": r"D:\dataset\FrUITeR\TestAnalyzer\input\extracted_tests\news\smartnews.csv",
        "Guardian": r"D:\dataset\FrUITeR\TestAnalyzer\input\extracted_tests\news\theguardian.csv",
        "USA TODAY": r"D:\dataset\FrUITeR\TestAnalyzer\input\extracted_tests\news\usatoday.csv",
        "5miles": r"D:\dataset\FrUITeR\TestAnalyzer\input\extracted_tests\shopping\5miles.csv",
        "6PM": r"D:\dataset\FrUITeR\TestAnalyzer\input\extracted_tests\shopping\6pm.csv",
        "AliExpress": r"D:\dataset\FrUITeR\TestAnalyzer\input\extracted_tests\shopping\aliexpress.csv",
        "Geek": r"D:\dataset\FrUITeR\TestAnalyzer\input\extracted_tests\shopping\geek.csv",
        "Home": r"D:\dataset\FrUITeR\TestAnalyzer\input\extracted_tests\shopping\home.csv",
        "Wish": r"D:\dataset\FrUITeR\TestAnalyzer\input\extracted_tests\shopping\wish.csv"
    }
    with open(answer_paths[db.app]) as f:
        reader = csv.DictReader(f)
        for line in reader:
            if db.test_name in line['method']:
                answers = json.loads(line['event_array'])
                break
    return answers


def get_success_num(answers, actions, xml_paths):
    skip = [
        "id@com.contextlogic.home:id/login_fragment_sign_in_button"
    ]
    answer_num = 0
    for i in range(len(actions)):
        while answers[answer_num]["id_or_xpath"] in skip:
            answer_num += 1
            if answer_num == len(answers):
                break
        if answer_num == len(answers):
            break
        if answers[answer_num]["action"] == "sendKeys":
            answers[answer_num]["action"] = "text"
        answers[answer_num]["id_or_xpath"] = re.sub(r'\[\d+\]', '', answers[answer_num]["id_or_xpath"])
        if check_success(answers[answer_num], actions[i], xml_paths[i]):
            answer_num += 1
        if answer_num == len(answers):
            break
    return answer_num


def check_success(answer, action, xml_path):
    if answer["action"] != action["action"]:
        return False
    if not answer["id_or_xpath"].startswith("xpath@/hierarchy") and check_action(answer, action):
        return True

    node_queue = deque()
    xpath_queue = deque()

    with open(xml_path, 'r', encoding="utf-8") as f:
        xml_dict = xmltodict.parse(f.read())

    if "node" in xml_dict["hierarchy"].keys():
        if isinstance(xml_dict["hierarchy"]["node"], list):
            for sub_node in reversed(xml_dict["hierarchy"]["node"]):
                if 'com.android.systemui' not in sub_node['@resource-id'] and 'com.android.systemui' not in sub_node['@package']:
                    node_queue.append(sub_node)
                    xpath_queue.append("/hierarchy/" + sub_node['@class'])
        else:
            if 'com.android.systemui' not in xml_dict["hierarchy"]["node"]['@resource-id'] and 'com.android.systemui' not in xml_dict["hierarchy"]["node"]['@package']:
                node_queue.append(xml_dict["hierarchy"]["node"])
                xpath_queue.append("/hierarchy/" + xml_dict["hierarchy"]["node"]['@class'])

    while len(node_queue) != 0:
        node = node_queue.pop()
        xpath = xpath_queue.pop()
        if 'com.android.systemui' in node['@resource-id'] or 'com.android.systemui' in node['@package']:
            continue

        if check_node_action(node, action):  # node为action节点
            node_queue.clear()
            xpath_queue.clear()
            if check_node_answer(node, xpath, answer):
                return True
            if "node" in node.keys():
                if isinstance(node["node"], list):
                    for sub_node in reversed(node["node"]):
                        node_queue.append(sub_node)
                        xpath_queue.append(xpath + "/" + sub_node['@class'])
                else:
                    node_queue.append(node["node"])
                    xpath_queue.append(xpath + "/" + node["node"]['@class'])

            while len(node_queue) != 0:
                node = node_queue.pop()
                xpath = xpath_queue.pop()
                if (node['@package'] == action['package'] and node['@enabled'] == 'true' and node['@visible-to-user'] == 'true' and
                        (node['@clickable'] == 'true' or
                         (node['@long-clickable'] == 'true' and 'EditText' not in node['@class']) or
                         (node['@scrollable'] == 'true' and 'Spinner' not in node['@class']) or
                         ('SeekBar' in node['@class'] and node['@clickable'] == 'false'))):
                    continue
                if check_node_answer(node, xpath, answer):  # node为answer节点，即action节点内部有answer节点，部件选取正确
                    return True
                if "node" in node.keys():
                    if isinstance(node["node"], list):
                        for sub_node in reversed(node["node"]):
                            node_queue.append(sub_node)
                            xpath_queue.append(xpath + "/" + sub_node['@class'])
                    else:
                        node_queue.append(node["node"])
                        xpath_queue.append(xpath + "/" + node["node"]['@class'])

            return False  # action节点内部无answer节点，部件选取错误

        if "node" in node.keys():
            if isinstance(node["node"], list):
                for sub_node in reversed(node["node"]):
                    node_queue.append(sub_node)
                    xpath_queue.append(xpath + "/" + sub_node['@class'])
            else:
                node_queue.append(node["node"])
                xpath_queue.append(xpath + "/" + node["node"]['@class'])

    return False  # 若从此处返回说明xml_path文件中无action节点，bug


def check_action(answer, action):
    if answer["id_or_xpath"].startswith("id@"):
        return action["resource-id"] == answer["id_or_xpath"][len("id@"):]
    else:
        info = answer["id_or_xpath"].split('"')[1]
        # if "@content-desc" in answer["id_or_xpath"]:
        #     return action["content-desc"] == info
        # elif "@text" in answer["id_or_xpath"]:
        #     return action["text"] == info
        # else:
        #     return False
        return action["content-desc"] == info or action["text"] == info


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


def check_node_answer(node_xml, xpath, answer):
    if answer["id_or_xpath"].startswith("id@"):
        change = {
            "id@com.thirdrock.fivemiles:id/main_tab_profile": "com.thirdrock.fivemiles:id/action_profile",
            "id@com.thirdrock.fivemiles:id/main_tab_search": "com.thirdrock.fivemiles:id/btn_category",
            "id@com.thirdrock.fivemiles:id/lbl_search": "com.thirdrock.fivemiles:id/home_toolbar_search",
            "id@com.thirdrock.fivemiles:id/cbx_sort_price_asc": "com.thirdrock.fivemiles:id/common_list_item_text",
            "id@com.contextlogic.home:id/search_mag_icon": "com.contextlogic.home:id/home_page_search_icon",
            "id@com.buzzfeed.android:id/search_bar": "com.buzzfeed.android:id/search_src_text"
        }
        if answer["id_or_xpath"] in change.keys() and node_xml["@resource-id"] == change[answer["id_or_xpath"]]:
            return True
        return node_xml["@resource-id"] == answer["id_or_xpath"][len("id@"):]
    elif answer["id_or_xpath"].startswith("xpath@/hierarchy"):
        return xpath == answer["id_or_xpath"][len("xpath@"):]
    else:
        info = answer["id_or_xpath"].split('"')[1]
        # if "@content-desc" in answer["id_or_xpath"]:
        #     return node_xml["@content-desc"] == info
        # elif "@text" in answer["id_or_xpath"]:
        #     return node_xml["@text"] == info
        # else:
        #     return False
        return node_xml["@content-desc"] == info or node_xml["@text"] == info


def prompt_one_test():
    test_name = db.app.replace(" ", "") + '_' + db.test_name
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
        xml_path = ui.dump_page_fr()
        actions = ui.analysis_state(xml_path)
        if len(actions) == 0:
            ui.handle_none_action()
            xml_path = ui.dump_page_fr()
            actions = ui.analysis_state(xml_path)
        prompt = LLM.get_prompt(xml_path, actions, action_list)
        with open(prompt_dir + "prompt" + str(len(action_list)) + ".txt", 'w', encoding='utf-8') as file:
            file.write(prompt)
        with open(action_dir + "action" + str(len(action_list)) + ".json", 'w', encoding='utf-8') as file:
            json.dump(actions, file, ensure_ascii=False, indent=4)

        prompt = db.few_shot + prompt  # few_shot
        if len(xml_path_list) != 0 and ui.check_two_page_same(pre_xml_path, xml_path):
            prompt = LLM.get_same_page_prompt(prompt, action_LLM)
        answer_LLM = LLM.decoder_for_deepseek(prompt, 256)
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
    success_num = get_success_num(answers, action_list, xml_path_list)

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

            user_input = input("test " + db.app.replace(" ", "") + '_' + line['test_name'] + ": " + line['test'] + ". Please press Enter to start.")
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
                    db.app.replace(" ", "") + '_' + db.test_name +
                    ":\nACP: " + str(success_num) + "/" + str(answer_num) + "=" + str(success_num / answer_num) +
                    "\nSUCCESS: " + str(success_num == answer_num) + "\n\n")

            # record AR
            if action_num == 0:
                with open(all_log_file_new, encoding="utf-8", mode="a") as file:
                    file.write(
                        db.app.replace(" ", "") + '_' + db.test_name +
                        ":\nAR: " + str(success_num) + "/" + str(action_num) + "=0.0" +
                        "\nSUCCESS: " + str(success_num == answer_num) + "\n\n")
            else:
                with open(all_log_file_new, encoding="utf-8", mode="a") as file:
                    file.write(
                        db.app.replace(" ", "") + '_' + db.test_name +
                        ":\nAR: " + str(success_num) + "/" + str(action_num) + "=" + str(success_num / action_num) +
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



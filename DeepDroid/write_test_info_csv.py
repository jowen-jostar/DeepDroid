import csv
import json
import re
import os
import LLM
try:
    from androguard.core.bytecodes.apk import APK
except ImportError:
    from androguard.core.apk import APK


def get_all_data_info():
    # function属性查询LLM得到:"What's xxx app? Please answer in one sentence."
    file_path = "PATH_to_FestiVal\\all_test_info.json"
    with open(file_path, 'r', encoding='utf-8') as file:
        datas = json.load(file)

    return datas


def write_csv_festival():
    datas = get_all_data_info()
    app = ""
    filename = './test_info.csv'  # 指定CSV文件名
    fieldnames = ["app", "test_name", "test", "function", "Manifest_xml", "AUT", "activities", "course"]  # CSV的列标题
    # 打开CSV文件进行写操作
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        # 写入列标题
        writer.writeheader()
        # 写入数据行
        for data in datas:
            if app != data["app"]:
                app = data["app"]
                activities_str = ""
                if data["apk_path"] != "":
                    apk = APK(data["apk_path"])
                    main_activity = apk.get_main_activity()
                    main_activity = main_activity[:main_activity.rfind('.')]
                    activities = apk.get_activities()
                    for i in range(len(activities)):
                        if activities[i].startswith(main_activity):
                            activities_str = activities_str + activities[i].split('.')[-1].replace('Activity', '') + ", "
                    activities_str = activities_str[:-2]
            row = {
                "app": data["app"],
                "test_name": data["test_name"],
                "test": data["target"],
                "function": data["function"],
                "Manifest_xml": data["apk_path"],
                "AUT": data["package"],
                "activities": activities_str,
                "course": "close"
            }
            writer.writerow(row)


def extract_function(java_code, function_name):
    # 正则表达式模式，用于匹配Java函数
    pattern = r'\b' + re.escape(function_name) + r'\b[^{]*\{[^}]*\}'
    # 搜索匹配的模式
    match = re.search(pattern, java_code)
    if match:
        return match.group()
    else:
        return None


def write_csv_fr():
    baned_app = ["cnn", "reuters", "newsrepublic", "theguardian", "aliexpress", "ebay", "etsy", "googleshopping", "groupon"]
    Manifest_xmls = {
        "abc": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\News\ABC News US World News_v5.4.6_apkpure.com.apk",
        "bbcnews": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\News\BBC News_v5.10.0_apkpure.com.apk",
        "buzzfeed": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\News\BuzzFeed News Tasty Quizzes_v2020.2_apkpure.com.apk",
        "cnn": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\News\CNN Breaking US World News_v6.6_apkpure.com.apk",
        "reuters": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\News\com.thomsonreuters.reuters_3.4.2-342_minAPI16(arm64-v8a,armeabi,armeabi-v7a,mips,mips64,x86,x86_64)(nodpi)_apkmirror.com.apk",
        "fox": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\News\Fox News Breaking News Live Video News Alerts_v3.29.2_apkpure.com.apk",
        "newsrepublic": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\News\News Republic Breaking and Trending News_v12.6.3.03_apkpure.com.apk",
        "smartnews": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\News\SmartNews Local Breaking News_v5.15.1_apkpure.com.apk",
        "theguardian": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\News\The Guardian Live World News Sport Opinion_v6.15.1903_apkpure.com.apk",
        "usatoday": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\News\USA TODAY_v5.23.2_apkpure.com.apk",
        "5miles": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\Shopping\5miles.apk",
        "6pm": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\Shopping\6pm.apk",
        "aliexpress": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\Shopping\aliexpress.apk",
        "ebay": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\Shopping\ebay.apk",
        "etsy": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\Shopping\etsy.apk",
        "geek": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\Shopping\geek.apk",
        "googleshopping": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\Shopping\googleshopping.apk",
        "groupon": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\Shopping\groupon.apk",
        "home": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\Shopping\home.apk",
        "wish": r"D:\dataset\FrUITeR\TestBenchmark-Java-client\subjects\Shopping\wish.apk"
    }
    filename = './test_info_fr.csv'  # 指定CSV文件名
    fieldnames = ["app", "test_name", "test", "function", "Manifest_xml", "AUT", "activities", "course"]  # CSV的列标题
    with open(filename, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file)
        # 写入列标题
        writer.writerow(fieldnames)

    for app_type in ["news", "shopping"]:
        for root, dirs, files in os.walk("D:\\dataset\\FrUITeR\\TestAnalyzer\\input\\extracted_tests\\" + app_type):
            for file in files:
                csv_path = os.path.join(root, file)
                file_name = file.split('.')[0]
                if file_name in baned_app:
                    continue
                Manifest_xml = Manifest_xmls[file_name]
                apk = APK(Manifest_xml)
                AUT = apk.get_package()
                app_name = apk.get_app_name()
                main_activity = apk.get_main_activity()
                activities = apk.get_activities()

                activities_str = ""
                main_activity = main_activity[:main_activity.rfind('.')]
                for i in range(len(activities)):
                    if activities[i].startswith(main_activity):
                        activities_str = activities_str + activities[i].split('.')[-1].replace('Activity', '') + ", "
                activities_str = activities_str[:-2]
                print(activities_str)

                function_prompt = "What's " + app_type + " app named " + app_name + "? Please answer in one sentence."
                print(function_prompt)
                function = LLM.decoder_for_deepseek(function_prompt, 128)
                print(function)

                with open(csv_path) as f:
                    reader = csv.DictReader(f)

                    app = ""
                    java_code = ""
                    for line in reader:
                        method = line['method']
                        test_name = method.split(' ')[2].split('(')[0]  # 要提取的函数名

                        if app == "":
                            app = method.split('.')[0][1:]
                            java_path = "D:\\dataset\\FrUITeR\\TestBenchmark-Java-client\\src\\main\\java\\" + app + "\\RepresentativeTests.java"
                            # 读取Java文件内容
                            with open(java_path, 'r') as java_file:
                                java_code = java_file.read()

                        # 提取函数
                        function_code = extract_function(java_code, test_name)
                        if function_code:
                            print(test_name + " Code:")
                            print("  " + function_code)
                            test_prompt = ("Please summarize the following function into a single task in one concise sentence "
                                           "without punctuation, such as 'set London as favourite without enabling notification' or "
                                           "'set London for favourites and set default location to London':\n\n  " + function_code)
                            test = LLM.decoder_for_deepseek(test_prompt, 128)
                            print(test)

                            # 打开CSV文件进行写操作
                            with open(filename, mode='a', newline='') as csv_file:
                                writer = csv.writer(csv_file)
                                # 写入数据行
                                writer.writerow([app_name, test_name, test, function, Manifest_xml, AUT, activities_str, "close"])
                        else:
                            print("Function " + test_name + " not found.")


if __name__ == "__main__":
    # write_csv_festival()
    write_csv_fr()


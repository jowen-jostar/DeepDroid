import uiautomator2 as u2
from DeepDroid.PreExplore.page_match import Structure, MatchUtil

# 保存已标注页面的信息
states = {}
# 保存已标注页面的路径，key：状态名，value：过程状态名，字符串数组
state_path = {}
structure_creator = Structure()
page_match = MatchUtil()
app_context = ""
target = ""
course = "close"
app = ""
activities = ""
test_name = ""
function = ""
test = ""
Manifest_xml = ""  # 开源应用存Manifest.xml路径，闭源应用存apk路径
AUT = ""

# needs to be modified ----------------------------------
api_key = "YOUR_API"
base_url = "https://api.deepseek.com"
email = "YOUR_EMAIL_for_APP_ACCOUNT"
password = "YOUR_PASSWORD_for_APP_ACCOUNT"
AVD_SERIAL = "YOUR_AVD_SERIAL"
DataSet_DIR = "PATH_to_FestiVal\\tests\\"
AllData_FILE = "PATH_to_FestiVal\\all_test_info.json"
max_character = 64  # text字段最大长度
# -------------------------------------------------------

# 连接设备
device = u2.connect(AVD_SERIAL)

few_shot = '''---Example---

I want to set London as favourite without enabling notification.
I have finished the following actions:
    (Step 1) {'action': 'click', 'text': 'Mountain View, CA', 'resource-id': 'location_button', 'class': 'android.widget.Button', 'content-desc': '', 'parent_node': 'global_toolbar', 'sibling_nodes': 'affiliate_logo', 'child_nodes': ''};
    (Step 2) {'action': 'text', 'text': 'Find Location', 'resource-id': 'location_search_box', 'class': 'android.widget.EditText', 'content-desc': '', 'parent_node': 'location_search', 'sibling_nodes': '', 'child_nodes': ''}.
Current GUI page have the following widgets that can be operated:
    (Widget Id: 0) {'action': 'click', 'text': '', 'resource-id': 'location_dialog', 'class': 'android.view.ViewGroup', 'content-desc': '', 'bounds': '[0,48][768,1184]', 'parent_node': 'content', 'sibling_nodes': '', 'child_nodes': 'location_dialog_container'};
    ......
    (Widget Id: 5) {'action': 'click', 'text': 'London, London, GB', 'resource-id': 'location_text', 'class': 'android.widget.TextView', 'content-desc': '', 'bounds': '[40,356][632,451]', 'parent_node': '', 'sibling_nodes': 'action_icon_container_added', 'child_nodes': ''};
    (Widget Id: 6) {'action': 'click', 'text': '', 'resource-id': 'action_icon_container_added', 'class': 'android.view.ViewGroup', 'content-desc': '', 'bounds': '[632,356][728,451]', 'parent_node': '', 'sibling_nodes': 'location_text/London, London, GB', 'child_nodes': 'action_icon_image_add_favorite, action_icon_text_add_favorite/Favorite'};
    ......
    (Widget Id: 22) {'action': 'click', 'text': '', 'resource-id': 'action_icon_container_added', 'class': 'android.view.ViewGroup', 'content-desc': '', 'bounds': '[632,1132][728,1184]', 'parent_node': '', 'sibling_nodes': 'location_text/London, Arkansas, US', 'child_nodes': 'action_icon_image_add_favorite'}.
Which widget id should I operate in this GUI page?

(Thought: To set London as a favorite without enabling notifications, we need to find the correct 'London' entry and click on the 'Favorite' icon next to it. The correct 'London' entry is 'London, London, GB', and the 'Favorite' icon next to it is Widget Id: 6, which has a sibling_node 'London, London, GB' and child_node 'Favorite'. Action: 6 Input: )

I want to set London for favourites and set default location to London.
I have finished the following actions:
    (Step 1) {'action': 'click', 'text': 'Mountain View, CA', 'resource-id': 'location_button', 'class': 'android.widget.Button', 'content-desc': '', 'parent_node': 'global_toolbar', 'sibling_nodes': 'affiliate_logo', 'child_nodes': ''};
    ......
    (Step 10) {'action': 'click', 'text': 'London', 'resource-id': 'city', 'class': 'android.widget.TextView', 'content-desc': '', 'parent_node': 'list_item_container', 'sibling_nodes': 'admin_area/United Kingdom', 'child_nodes': ''}.
Current GUI page have the following widgets that can be operated:
    (Widget Id: 0) {'action': 'click', 'text': '', 'resource-id': '', 'class': 'android.widget.ImageButton', 'content-desc': 'Navigate up', 'bounds': '[0,48][112,160]', 'parent_node': 'toolbar', 'sibling_nodes': 'global_toolbar', 'child_nodes': ''};
    ......
    (Widget Id: 5) {'action': 'click', 'text': '', 'resource-id': 'list_item_container', 'class': 'android.view.ViewGroup', 'content-desc': '', 'bounds': '[0,582][768,713]', 'parent_node': 'default_locations_favorites_list', 'sibling_nodes': '', 'child_nodes': 'city/London, admin_area/United Kingdom'}.
Which widget id should I operate in this GUI page?

(Thought: The task is to set London as the default location. In Step 10, London was already selected as the default location. No further action is needed as the task is complete. Action: -1 Input: )

---End Example---

'''
import uiautomator2 as u2
from DeepDroid.PreExplore.page_match import Structure, MatchUtil


AUT = ""
app_function = ""
current_event = []
# 保存已标注页面的信息
states = {}
# 保存已标注页面的路径，key：状态名，value：过程状态名，字符串数组
state_path = {}
# 当前路径，字符串数组
path = []
structure_creator = Structure()
page_match = MatchUtil()

# needs to be modified ----------------------------------
# 连接设备
AVD_SERIAL = "YOUR_AVD_SERIAL"
device = u2.connect(AVD_SERIAL)
# episode的最大步长，即执行60个操作后结束
max_step = 60
# -------------------------------------------------------

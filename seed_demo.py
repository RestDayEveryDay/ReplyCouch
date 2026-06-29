"""演示用：灌入一批真实感的场景聊天档案，填满分页（至少 2 个完整页面）。

用法（在 reply-coach 目录下，确保后端在 8000 跑着）：
    python3 seed_demo.py            # 清掉旧档案 + 灌 18 条
    python3 seed_demo.py --keep     # 不清旧的，只追加
"""
import json
import sys
import urllib.request

BASE = "http://localhost:8000"


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def clear_all():
    # 把可见 + 隐藏的都清掉
    for hidden in (0, 1):
        while True:
            d = api("GET", f"/api/archives?page=1&page_size=50&hidden={hidden}")
            items = d.get("items", [])
            if not items:
                break
            for it in items:
                api("DELETE", f"/api/archives/{it['id']}")


ARCHIVES = [
    # ---------------- 心动对象 crush ----------------
    {"name": "林晚（同系学妹）", "scenario": "crush",
     "my_sliders": {"ie": 35, "cw": 40, "sa": 70, "pa": 30},
     "their_sliders": {"ie": 65, "cw": 75, "sa": 60, "pa": 55},
     "my_detail": "我比较慢热，喜欢她但没表白，怕破坏现在的关系", "their_detail": "回消息快，爱发表情包，最近会主动找我",
     "relation_text": "认识三个月，一起上过选修课，最近常一起去图书馆",
     "chat_history": "对方：你今天去图书馆吗\n我：去啊 你也去？\n对方：嗯 老位置见\n我：好 我带了你上次说想吃的牛轧糖\n对方：啊啊你还记得！太好了\n我：随口一提你就馋上了 哈哈\n对方：被你发现了 那等你哦"},
    {"name": "陈屿（健身房认识）", "scenario": "crush",
     "my_sliders": {"ie": 60, "cw": 30, "sa": 50, "pa": 75},
     "their_sliders": {"ie": 30, "cw": 55, "sa": 40, "pa": 35},
     "my_detail": "直球派，看对眼了就想约", "their_detail": "话不多，但每次都回，约了两次都来了",
     "relation_text": "健身房搭话认识两周，加了微信",
     "chat_history": "对方：今天没看到你来练\n我：临时加班了 你居然注意到\n对方：你那组卧推动静挺大的\n我：哈哈下次轻点 周末一起吃个饭？\n对方：可以啊 你定地方"},
    {"name": "苏念（前同事）", "scenario": "crush",
     "my_sliders": {"ie": 45, "cw": 50, "sa": 65, "pa": 40},
     "their_sliders": {"ie": 70, "cw": 80, "sa": 75, "pa": 60},
     "my_detail": "离职后才发现有点喜欢她", "their_detail": "性格开朗自来熟，朋友很多",
     "relation_text": "前同事，离职后还保持联系，偶尔约饭",
     "chat_history": "对方：诶你走了之后我们组好无聊\n我：怎么 没人陪你摸鱼了\n对方：对！而且午饭都没人一起吐槽食堂了\n我：那周五我回去附近 一起？\n对方：好呀好呀 我跟你说最近好多瓜"},
    {"name": "周一（豆瓣网友）", "scenario": "crush",
     "my_sliders": {"ie": 25, "cw": 45, "sa": 80, "pa": 35},
     "their_sliders": {"ie": 40, "cw": 60, "sa": 85, "pa": 45},
     "my_detail": "线上聊得来，还没见过面", "their_detail": "很会玩梗，聊天很有节奏感",
     "relation_text": "豆瓣同好小组认识，聊了一个多月",
     "chat_history": "对方：你头像那只猫是你的吗\n我：是啊 主子名叫年糕\n对方：哈哈哈这名字 是不是很黏人\n我：黏到我打字它都要躺键盘上\n对方：那我有点羡慕这只猫了\n我：？？\n对方：没什么 晚安"},
    {"name": "Vivian（相亲对象）", "scenario": "crush",
     "my_sliders": {"ie": 50, "cw": 40, "sa": 45, "pa": 50},
     "their_sliders": {"ie": 55, "cw": 50, "sa": 40, "pa": 50},
     "my_detail": "家里安排的相亲，第一印象还不错", "their_detail": "得体大方，聊天有分寸",
     "relation_text": "相亲认识，见过一面，互相加了微信",
     "chat_history": "对方：今天聊得挺开心的 到家了吗\n我：刚到 今天谢谢你的咖啡\n对方：客气啦 下次轮到你请\n我：那说定了 你周末一般怎么安排\n对方：看情况 有好去处随时叫我"},
    {"name": "阿凯（剧本杀搭子）", "scenario": "crush",
     "my_sliders": {"ie": 55, "cw": 35, "sa": 75, "pa": 65},
     "their_sliders": {"ie": 60, "cw": 70, "sa": 80, "pa": 55},
     "my_detail": "玩剧本杀认识，很合拍", "their_detail": "戏精，玩得开，私下也好聊",
     "relation_text": "剧本杀固定搭子，组了三四次局",
     "chat_history": "对方：周六那个硬核本约吗\n我：约 不过上次你坑我\n对方：哪有 我那是演技\n我：行吧 这次别再背刺我了\n对方：不背刺你了 这次保护你"},

    # ---------------- 导师 mentor ----------------
    {"name": "张老师（毕设导师）", "scenario": "mentor",
     "my_sliders": {"ie": 30, "se": 50, "ra": 40, "qt": 35},
     "their_sliders": {"ie": 40, "se": 25, "ra": 30, "qt": 45},
     "my_detail": "研三，毕设进度有点慢，怕导师不满意", "their_detail": "要求严，但人挺好，就是话直",
     "relation_text": "跟了两年的导师，最近因为论文进度有点紧张",
     "chat_history": "对方：这周的实验结果出来了吗\n我：出来一部分 还有两组在跑\n对方：进度比预期慢了\n我：是 我这周末加一下\n对方：周一组会你先讲讲思路 别只报数据"},
    {"name": "李导（实习 mentor）", "scenario": "mentor",
     "my_sliders": {"ie": 45, "se": 55, "ra": 60, "qt": 40},
     "their_sliders": {"ie": 50, "se": 40, "ra": 70, "qt": 60},
     "my_detail": "实习生，想请两天假回学校答辩", "their_detail": "看重结果，但比较通情达理",
     "relation_text": "实习公司带我的 mentor，处了三个月",
     "chat_history": "对方：你那个需求今天能提测吗\n我：能 下午之前提\n我：另外想跟您请个假 下周三四要回学校答辩\n对方：提前把手头的交接好就行\n我：好的 我今天列个清单发您"},
    {"name": "王教授（组会）", "scenario": "mentor",
     "my_sliders": {"ie": 25, "se": 45, "ra": 35, "qt": 30},
     "their_sliders": {"ie": 35, "se": 20, "ra": 25, "qt": 70},
     "my_detail": "博一，刚进组，还在摸索方向", "their_detail": "话很多，喜欢追问，容易紧张",
     "relation_text": "刚进组三个月，还在适应导师风格",
     "chat_history": "对方：上次让你读的那几篇 有想法没\n我：有一点 我觉得第二篇的方法可以借鉴\n对方：具体哪里 说说看\n我：它的采样策略 或许能用到我们的场景\n对方：嗯 下次组会展开讲 别只给结论"},
    {"name": "赵老师（推荐信）", "scenario": "mentor",
     "my_sliders": {"ie": 40, "se": 60, "ra": 50, "qt": 35},
     "their_sliders": {"ie": 45, "se": 35, "ra": 55, "qt": 50},
     "my_detail": "想请老师写推荐信，怕打扰", "their_detail": "比较忙，但对学生不错",
     "relation_text": "上过两门课的任课老师，关系不算太近",
     "chat_history": "对方：你说的申请 截止是什么时候\n我：12 月初 想麻烦您写封推荐信\n对方：可以 你把简历和 PS 发我\n我：好的 这就整理 谢谢老师\n对方：材料齐了提醒我一声"},

    # ---------------- 面试官 / HR interviewer ----------------
    {"name": "美团 HR-周", "scenario": "interviewer",
     "my_sliders": {"ie": 50, "fw": 60, "sf": 55, "sd": 65},
     "their_sliders": {"ie": 45, "fw": 30, "sf": 60, "sd": 50},
     "my_detail": "三面通过了，在等 offer，手上还有别的流程", "their_detail": "回复及时，态度友好",
     "relation_text": "面到三面，HR 说在走审批",
     "chat_history": "对方：你好 三面反馈不错 我们在走内部流程\n我：好的 感谢告知 大概多久有结果\n对方：本周内应该能定 有进展第一时间同步你\n我：好的 我这边还有一个流程在推进 麻烦您也帮我留意下时间\n对方：理解 我尽量帮你催一下"},
    {"name": "字节-面试官陈", "scenario": "interviewer",
     "my_sliders": {"ie": 45, "fw": 55, "sf": 70, "sd": 60},
     "their_sliders": {"ie": 40, "fw": 25, "sf": 75, "sd": 70},
     "my_detail": "二面被问得很细，感觉一般", "their_detail": "节奏快，问题很硬",
     "relation_text": "刚面完二面，等通知",
     "chat_history": "对方：今天辛苦了 后面有结果会通过 HR 通知你\n我：好的 谢谢您 今天那道系统设计我答得不太理想\n对方：整体思路是对的 细节可以再打磨\n我：受教了 那我等后续通知\n对方：嗯 保持手机畅通"},
    {"name": "腾讯 HR-林", "scenario": "interviewer",
     "my_sliders": {"ie": 55, "fw": 65, "sf": 45, "sd": 55},
     "their_sliders": {"ie": 50, "fw": 40, "sf": 50, "sd": 45},
     "my_detail": "想谈一下薪资，怕开高了被刷", "their_detail": "公事公办，但好沟通",
     "relation_text": "终面通过，进入谈薪环节",
     "chat_history": "对方：恭喜通过终面 想跟你聊下薪资期望\n我：谢谢 我目前期望是在现有基础上有一定涨幅\n对方：方便给个具体区间吗\n我：我把目前的构成和期望整理一下发您 您看是否合理\n对方：好 收到后我帮你争取"},
    {"name": "小红书-猎头王", "scenario": "interviewer",
     "my_sliders": {"ie": 40, "fw": 50, "sf": 60, "sd": 70},
     "their_sliders": {"ie": 55, "fw": 60, "sf": 65, "sd": 55},
     "my_detail": "猎头推的岗位，还在观望", "their_detail": "热情，推进很积极",
     "relation_text": "猎头联系的机会，聊了 JD",
     "chat_history": "对方：这个岗位我觉得跟你很匹配 要不要安排聊一下\n我：可以先了解一下 团队和方向大概是怎样的\n对方：我把详细 JD 和团队介绍发你\n我：好 我看完给你答复\n对方：别犹豫太久 这个 head count 比较抢手"},

    # ---------------- 长辈亲戚 elder ----------------
    {"name": "三姨（家族群）", "scenario": "elder",
     "my_sliders": {"ie": 40, "to": 30, "fe": 55, "rc": 70},
     "their_sliders": {"ie": 60, "to": 25, "fe": 65, "rc": 80},
     "my_detail": "想婉拒三姨的相亲安排", "their_detail": "热心肠，爱张罗，话多",
     "relation_text": "三姨最近总在群里张罗给我介绍对象",
     "chat_history": "对方：给你介绍的那个小伙子 加微信了吗\n我：三姨 我最近工作太忙了 实在没精力\n对方：再忙也得考虑终身大事呀\n我：我知道您是为我好 等忙过这阵我自己留意着\n对方：那行 阿姨先帮你留着"},
    {"name": "爷爷", "scenario": "elder",
     "my_sliders": {"ie": 35, "to": 20, "fe": 45, "rc": 50},
     "their_sliders": {"ie": 45, "to": 15, "fe": 50, "rc": 40},
     "my_detail": "想报个平安，顺便岔开催婚话题", "their_detail": "传统，但很疼我",
     "relation_text": "爷爷身体还硬朗，隔几天打个字给我",
     "chat_history": "对方：天冷了 记得添衣服\n我：知道啦爷爷 您也注意保暖\n对方：什么时候回来看看\n我：过年一定回 给您带您爱吃的桃酥\n对方：好好好 路上注意安全"},
    {"name": "大伯（转发养生）", "scenario": "elder",
     "my_sliders": {"ie": 45, "to": 35, "fe": 50, "rc": 40},
     "their_sliders": {"ie": 50, "to": 20, "fe": 60, "rc": 75},
     "my_detail": "大伯老转养生谣言，想礼貌提醒又不伤和气", "their_detail": "热心,容易信养生文章",
     "relation_text": "大伯爱在群里转发各种养生帖",
     "chat_history": "对方：转发：这五种食物千万别一起吃 会中毒\n我：大伯 这个其实是谣言啦 正规吃没事的\n对方：是吗 那我看着挺像真的\n我：现在这种标题党挺多的 您看的时候多留个心\n对方：还是你们年轻人懂 行 我以后注意"},
    {"name": "小姑", "scenario": "elder",
     "my_sliders": {"ie": 50, "to": 45, "fe": 40, "rc": 55},
     "their_sliders": {"ie": 55, "to": 50, "fe": 45, "rc": 60},
     "my_detail": "小姑问工资问得有点多", "their_detail": "比较开明，但好奇心强",
     "relation_text": "小姑平时联系不多，过节才聊",
     "chat_history": "对方：现在一个月挣多少呀\n我：够花啦小姑 就是普通打工人\n对方：那有没有攒下钱\n我：在慢慢攒 您放心 我心里有数\n对方：那就好 别太省 该吃吃该穿穿"},
]


# 关系阶段（驱动仪表盘的状态：升温 / 平平 / 需注意）
STAGE_BY_NAME = {
    "林晚（同系学妹）": "暧昧中", "陈屿（健身房认识）": "有点意思", "苏念（前同事）": "有点意思",
    "周一（豆瓣网友）": "暧昧中", "Vivian（相亲对象）": "刚认识", "阿凯（剧本杀搭子）": "有点意思",
    "张老师（毕设导师）": "有点压力", "李导（实习 mentor）": "正常往来", "王教授（组会）": "刚进组",
    "赵老师（推荐信）": "正常往来", "美团 HR-周": "在等结果", "字节-面试官陈": "在等结果",
    "腾讯 HR-林": "流程推进中", "小红书-猎头王": "初步沟通", "三姨（家族群）": "有点代沟",
    "爷爷": "走得挺近", "大伯（转发养生）": "有点代沟", "小姑": "平常往来",
}

# 给「本周问军师」指标喂真实历史：调用 generate 会写入 history（离线引擎也写）
HISTORY_SEED = [
    ("crush", "对方：在吗 周末有空不", "想约她出来"),
    ("crush", "对方：哈哈哈你好搞笑", ""),
    ("crush", "对方：最近好忙 改天吧", "想确认还有没有戏"),
    ("mentor", "对方：这周进度怎么样", "想说还差一点"),
    ("mentor", "对方：组会你来讲一下", ""),
    ("interviewer", "对方：我们还在走流程", "想催一下结果"),
    ("interviewer", "对方：期望薪资多少", "想谈薪资"),
    ("elder", "对方：有对象了吗", "想婉拒"),
    ("elder", "对方：转发：这五种食物不能吃", "想提醒是谣言"),
    ("crush", "对方：你头像挺好看", ""),
    ("mentor", "对方：论文我看了 问题不少", "想约时间当面聊"),
    ("interviewer", "对方：你还有什么想问的吗", "想问后续安排"),
]


def seed_history():
    print(f"灌入 {len(HISTORY_SEED)} 条「问军师」历史…")
    for scenario, chat, intent in HISTORY_SEED:
        try:
            api("POST", "/api/generate", {"scenario": scenario, "chat_history": chat, "intent": intent})
        except Exception as e:
            print("  ! 跳过一条:", e)


def main():
    keep = "--keep" in sys.argv
    if not keep:
        print("清空旧档案…")
        clear_all()
    print(f"灌入 {len(ARCHIVES)} 条真实场景档案…")
    for a in ARCHIVES:
        a["relation_stage"] = STAGE_BY_NAME.get(a["name"], "")
        r = api("POST", "/api/archives", a)
        print("  +", r.get("name"), "·", a["relation_stage"])
    seed_history()
    d = api("GET", "/api/archives?page=1&page_size=8")
    print(f"完成。共 {d['total']} 段，page_size=8 → {d['pages']} 页。")


if __name__ == "__main__":
    main()

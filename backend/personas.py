"""场景、双方性格画像、语气档位的静态定义。"""

SCENARIOS = [
    {
        "id": "crush",
        "name": "Crush",
        "icon": "💘",
        "desc": "暧昧期的每句话都想说得刚刚好",
        "base_risk": 50,
        "examples": ["在吗？", "哈哈哈你也太搞笑了", "改天一起吃饭吧"],
        "stages": ["刚认识", "普通朋友", "有点意思", "暧昧中", "陷入僵局"],
        "relation_label": "你俩现在",
        "record_label": "这段关系的记录",
        "relation_hint": "一句话说说你俩的关系和近况：认识多久、走到哪一步、最近发生了什么…",
        "sliders": [
            {"id": "ie", "left": "内向", "right": "外向"},
            {"id": "cw", "left": "高冷", "right": "热情"},
            {"id": "sa", "left": "正经", "right": "抽象"},
            {"id": "pa", "left": "被动", "right": "主动"},
        ],
        "consult": [
            "ta 是不是喜欢我",
            "我是不是喜欢 ta",
            "我们是不是互相喜欢",
            "ta 最近为什么变冷淡了",
            "现在该主动还是该等一等",
            "这段关系还值得继续吗",
        ],
        "ask_hint": "问军师：ta 是不是喜欢我？该不该主动？",
        "intent_hint": "想说啥（可选）：比如想约 ta 周末看电影，但不知道咋开口",
    },
    {
        "id": "mentor",
        "name": "导师/前辈",
        "icon": "🎓",
        "desc": "汇报进度、请假、约谈话的艺术",
        "base_risk": 45,
        "examples": ["来我办公室一趟", "论文我看了，问题比较多", "这周组会你来讲"],
        "stages": ["刚进组", "正常往来", "比较受认可", "有点压力", "闹过别扭"],
        "relation_label": "目前的关系",
        "record_label": "这段对话的记录",
        "relation_hint": "一句话说说目前的情况：跟了多久、最近在忙什么、有没有要紧的节点…",
        "sliders": [
            {"id": "ie", "left": "内向", "right": "外向"},
            {"id": "se", "left": "严厉", "right": "随和"},
            {"id": "ra", "left": "看重结果", "right": "看重态度"},
            {"id": "qt", "left": "话少", "right": "话密"},
        ],
        "consult": [
            "导师对我满不满意",
            "导师是不是对我有意见了",
            "这样回会不会显得不上心",
            "该不该催一下导师",
            "我是不是惹导师不高兴了",
            "这事该当面说还是发消息",
        ],
        "ask_hint": "问军师：导师这话什么意思？该怎么回比较稳妥？",
        "intent_hint": "想说啥（可选）：比如想请两天假、想约时间汇报进度",
    },
    {
        "id": "interviewer",
        "name": "面试官 / HR",
        "icon": "💼",
        "desc": "跟进流程、谈薪资、回复 offer",
        "base_risk": 50,
        "examples": ["你的期望薪资是多少？", "我们这边还在走流程", "你还有什么想问的吗？"],
        "stages": ["刚投递", "初步沟通", "流程推进中", "在等结果", "快凉了"],
        "relation_label": "当前进展",
        "record_label": "这段对话的记录",
        "relation_hint": "一句话说说进展：投了什么岗、面到第几轮、目前卡在哪…",
        "sliders": [
            {"id": "ie", "left": "内向", "right": "外向"},
            {"id": "fw", "left": "公事公办", "right": "亲和"},
            {"id": "sf", "left": "节奏慢", "right": "节奏快"},
            {"id": "sd", "left": "含蓄", "right": "直接"},
        ],
        "consult": [
            "我这轮还有戏吗",
            "这是不是委婉拒绝",
            "该不该催面试结果",
            "现在能不能谈薪资",
            "多久没消息算凉了",
            "要不要主动跟进一下",
        ],
        "ask_hint": "问军师：HR 这话是什么信号？该怎么跟进？",
        "intent_hint": "想说啥（可选）：比如想问进度、想谈薪资、想回复 offer",
    },
    {
        "id": "elder",
        "name": "长辈亲戚",
        "icon": "🧧",
        "desc": "家族群里的得体艺术",
        "base_risk": 30,
        "examples": ["有对象了吗？", "工作找得怎么样了", "转发：这十种食物千万不能吃"],
        "stages": ["不太熟", "平常往来", "走得挺近", "有点代沟", "有过摩擦"],
        "relation_label": "平时的相处",
        "record_label": "这段对话的记录",
        "relation_hint": "一句话说说平时的相处：多久联系一次、最近聊过什么、有没有要忌讳的…",
        "sliders": [
            {"id": "ie", "left": "内向", "right": "外向"},
            {"id": "to", "left": "传统", "right": "开明"},
            {"id": "fe", "left": "强势", "right": "随和"},
            {"id": "rc", "left": "寡言", "right": "唠叨"},
        ],
        "consult": [
            "这话是不是话里有话",
            "怎么回才不尴尬",
            "怎么把话题礼貌岔开",
            "怎么婉拒不伤和气",
            "这条该不该认真回",
            "ta 是不是在催我",
        ],
        "ask_hint": "问军师：长辈这话什么意思？怎么回得体？",
        "intent_hint": "想说啥（可选）：比如想婉拒、想岔开话题、想报个平安",
    },
]

MY_PERSONAS = [
    {"id": "zhiqiu", "name": "直球派", "icon": "🎯", "desc": "有话直说，不爱绕弯"},
    {"id": "manre", "name": "慢热派", "icon": "🐢", "desc": "需要时间升温，表达谨慎"},
    {"id": "youmo", "name": "幽默派", "icon": "🤡", "desc": "什么场合都想抖个机灵"},
    {"id": "jinshen", "name": "谨慎派", "icon": "🛡️", "desc": "每条消息都要斟酌三遍"},
]

THEIR_PERSONAS = [
    {"id": "gaoleng", "name": "高冷型", "icon": "🧊", "desc": "话少、回复慢、捉摸不透"},
    {"id": "reqing", "name": "热情型", "icon": "🔥", "desc": "回复快，表情包连发"},
    {"id": "yansu", "name": "严肃忙碌型", "icon": "📋", "desc": "公事公办，时间宝贵"},
    {"id": "yinqing", "name": "阴晴不定型", "icon": "🌦️", "desc": "上一秒哈哈哈，下一秒嗯"},
]

RELATION_STAGES = [
    {"id": "fresh", "label": "刚认识"},
    {"id": "friends", "label": "普通朋友"},
    {"id": "fuzzy", "label": "有点意思"},
    {"id": "ambiguous", "label": "暧昧中"},
    {"id": "cold", "label": "陷入僵局"},
]

GENDERS = [
    {"id": "male", "label": "男", "icon": "👦"},
    {"id": "female", "label": "女", "icon": "👧"},
]

TONES = [
    {"id": "safe", "label": "稳妥", "icon": "🛡️"},
    {"id": "natural", "label": "自然", "icon": "🌿"},
    {"id": "bold", "label": "大胆", "icon": "🔥"},
]


def by_id(items, item_id):
    for item in items:
        if item["id"] == item_id:
            return item
    return None


def _bucket(value, left, right):
    """把 0-100 的滑轨值翻成一句人话。50 附近视为「居中」，不强行贴标签。"""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return None
    if v <= 18:
        return f"非常{left}"
    if v <= 38:
        return f"偏{left}"
    if v < 62:
        return None  # 居中：不输出，避免每条都凑字
    if v < 82:
        return f"偏{right}"
    return f"非常{right}"


def describe_sliders(scenario, values):
    """scenario：场景 dict；values：{滑轨id: 0-100}。返回「偏外向、有点高冷、偏主动」式描述。"""
    if not scenario or not values:
        return ""
    parts = []
    for s in scenario.get("sliders", []):
        phrase = _bucket(values.get(s["id"]), s["left"], s["right"])
        if phrase:
            parts.append(phrase)
    return "、".join(parts)

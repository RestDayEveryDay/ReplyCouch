"""回复生成引擎。

双模式：
- 离线规则引擎（默认）：零依赖、零配置，保证课堂演示永远可用（Wizard-of-Oz 路径）。
- LLM 引擎：设置 ANTHROPIC_API_KEY 后启用，由 Claude 生成回复；任何异常自动降级回离线引擎。
"""

import json
import os
import re

from . import personas

ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL") or None
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen-vl-max")
QWEN_BASE_URL = os.environ.get(
    "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# ---------------------------------------------------------------- 潜台词分析（离线）

SIGNAL_RULES = [
    (r"在吗|在不在|忙吗", "「在吗」式开场：对方在试探你的可用性，后面多半有正事或想聊的话题", 8, "👀"),
    (r"^(哦+|嗯+|噢|哦哦)[。.~～!！]?$", "极简回应：可能在忙，也可能兴致不高。降低输出密度，别刷屏", 20, "🥶"),
    (r"呵呵", "「呵呵」出现：高危信号，多数语境下表示冷淡或不满", 25, "🚨"),
    (r"改天|下次|再说|有空再|以后再", "软性推迟：没有给出具体时间，优先级存疑，别追问太紧", 15, "⏳"),
    (r"哈哈哈|hhh+|笑死|xswl|XSWL", "高频笑声：气氛轻松，对方愿意维持对话", -12, "😄"),
    (r"？？|\?\?|怎么还|为什么没|到底", "连环追问：对方带着情绪或急迫感，先回应情绪再讲事情", 18, "⚡"),
    (r"忙|开会|没时间|赶due|加班", "时间压力：对方很忙，回复宜短、给台阶、给确定性", 10, "⏰"),
    (r"尽快|今天之内|明天前|截止|ddl|DDL", "明确期限：先给确定性答复，再补细节", 15, "📌"),
    (r"谢谢|辛苦|麻烦你", "客气模式：礼尚往来即可，不必过度解读", -5, "🤝"),
    (r"！|!", "感叹号：情绪能量较高", -5, "✨"),
    (r"[😀-🙏]|\[表情\]|～|~", "带表情/语气词：沟通门槛不高，可以放松一点", -8, "🙂"),
]


def risk_label(score):
    if score < 35:
        return "稳的"
    if score < 65:
        return "悠着点"
    return "别浪"


def analyze(received, scenario):
    signals = []
    risk = scenario["base_risk"]
    for pattern, meaning, delta, icon in SIGNAL_RULES:
        if re.search(pattern, received):
            signals.append({"icon": icon, "meaning": meaning})
            risk += delta
    if not signals:
        if len(received.strip()) <= 5:
            signals.append({"icon": "🔍", "meaning": "短消息信息量低，注意不要过度解读"})
            risk += 5
        else:
            signals.append({"icon": "🌤️", "meaning": "没有明显情绪信号，按常规节奏回复即可"})
    risk = max(5, min(95, risk))
    return {"risk": risk, "risk_label": risk_label(risk), "signals": signals[:5]}


def _extract_latest(chat_history):
    """从完整聊天记录中提取对方最后一条消息，供离线引擎分析用。"""
    if not chat_history:
        return ""
    lines = [l.strip() for l in chat_history.strip().splitlines() if l.strip()]
    if not lines:
        return ""
    MY_PREFIXES = ("我:", "我：", "me:", "me：")
    THEIR_PREFIXES = ("对方:", "对方：", "ta:", "ta：", "他:", "他：", "她:", "她：")
    for line in reversed(lines):
        low = line.lower()
        if any(low.startswith(p.lower()) for p in MY_PREFIXES):
            continue
        for p in THEIR_PREFIXES:
            if low.startswith(p.lower()):
                return line[len(p):].strip()
        return line  # 无前缀行默认视为对方消息
    return lines[-1]


# ---------------------------------------------------------------- 离线模板引擎

def normalize_intent(intent):
    s = (intent or "").strip().rstrip("。.!！~～")
    s = re.sub(r"^(我想要|我想|我打算|我希望|想要|想|希望)", "", s)
    s = s.replace("她", "你").replace("TA", "你").replace("ta", "你")
    return s


TEMPLATES = {
    "crush": {
        "safe": ("{opener}{i}～有空的话啦 没空也完全 ok 的哈哈",
                 "{opener}哈哈哈哈看到啦 你今天咋样"),
        "natural": ("{opener}诶我正好想说{i}来着 你说巧不巧",
                    "{opener}刚想找你呢 这不就双向奔赴了（"),
        "bold": ("{opener}第一条：{i} 第二条：不许拒绝那种",
                 "{opener}说真的 跟你聊天我能笑一整天 你是懂怎么把我逗乐的"),
    },
    "mentor": {
        "safe": ("{opener}老师您好，{i}，您看什么时候方便？麻烦您了，谢谢老师！",
                 "{opener}好的老师，收到！我马上处理。"),
        "natural": ("{opener}老师好～{i}，想先听听您的建议。",
                    "{opener}收到老师！我整理一下目前的进展发给您。"),
        "bold": ("{opener}老师您好，{i}。相关材料我已经准备好了，您方便的话我随时可以来办公室当面汇报。",
                 "{opener}老师，我有几个想法想跟您当面聊聊，您这周哪天方便？"),
    },
    "interviewer": {
        "safe": ("{opener}您好，感谢您的消息。{i}，期待您的回复，谢谢！",
                 "{opener}您好，收到，感谢告知！"),
        "natural": ("{opener}您好！{i}。另外想了解一下后续的安排，谢谢～",
                    "{opener}好的，感谢！请问后续流程大概是怎样的呢？"),
        "bold": ("{opener}您好，感谢反馈。{i}。另外我手头有其他流程在推进，想确认一下贵司的时间节点，方便我统筹安排，谢谢！",
                 "{opener}感谢！想确认一下结果大概什么时候出——我手头还有其他 offer 在等回复。"),
    },
    "elder": {
        "safe": ("{opener}谢谢关心呀！{i}😊 您也多保重身体～",
                 "{opener}哈哈是呀是呀，您说得对！"),
        "natural": ("{opener}{i}，等放假回去看您们！",
                    "{opener}收到收到！您发的我都看啦，很有用！"),
        "bold": ("{opener}哈哈{i}！到时候咱们好好聚一聚，我还要跟您讨教讨教呢",
                 "{opener}哎呀这您就问对人了，等见面我跟您细说！"),
    },
}

EMOJIS = {
    "crush": {"safe": "😊（一个就好，多了显刻意）", "natural": "😄✨", "bold": "🙈 + 一张你们之间的梗图"},
    "mentor": {"safe": "🙏（或不加，更稳）", "natural": "😊", "bold": "不加表情，显专业"},
    "interviewer": {"safe": "不加表情", "natural": "不加表情，或一个😊", "bold": "不加表情"},
    "elder": {"safe": "😊🙏", "natural": "😊🌹（长辈最爱玫瑰）", "bold": "🧧😄 + 长辈风祝福图"},
}

THEIR_ADVICE = {
    "gaoleng": {
        "safe": "高冷型吃「不施压」这套：留足空间，球抛过去就停",
        "natural": "高冷型话少但都看在眼里，自然一点，别用力过猛",
        "bold": "对高冷型发直球是高风险高回报，确认最近有来有回再发",
    },
    "reqing": {
        "safe": "热情型不喜欢太拘谨的回复，稳妥版记得保留一点温度",
        "natural": "和热情型同频最重要，跟上对方的节奏就赢了一半",
        "bold": "热情型对大胆表达接受度高，这版收益不错、风险可控",
    },
    "yansu": {
        "safe": "严肃忙碌型最认这种：信息完整、一条说清、不浪费时间",
        "natural": "对严肃型可以自然，但结构要清楚：结论先行",
        "bold": "对严肃型「大胆」=主动给方案，而不是套近乎，这版踩在点上",
    },
    "yinqing": {
        "safe": "阴晴不定型先看天气再说话，这版进可攻退可守，最稳",
        "natural": "对方情绪不明时，自然版既不冷场也不越界",
        "bold": "强烈建议先用消息试探下气氛，确认是晴天再发这版",
    },
}

MY_STYLE_NOTES = {
    "zhiqiu": {"bold": "你是直球派，这版最顺手——但记得给对方留接话的空间"},
    "manre": {"bold": "你是慢热派，发之前确认这是你想说的，而不是上头"},
    "youmo": {"safe": "你是幽默派，稳妥版可能不太像你，可以加一点自己的梗"},
    "jinshen": {"bold": "你是谨慎派，这版建议打完放十秒、再读一遍再发"},
}


OFFLINE_TONE_NOTE = {
    "safe": "稳一点的版本，拿不准对方状态时最保险",
    "natural": "日常自然的语气，最不容易出错",
    "bold": "更主动大胆，气氛好的时候用",
}


def offline_generate(scenario, received, intent, my_profile="", their_profile=""):
    analysis = analyze(received, scenario)
    formal = scenario["id"] in ("mentor", "interviewer")

    opener = ""
    if re.search(r"在吗|在不在|忙吗", received):
        opener = "在的，您说。" if formal else "在的在的～"
    elif re.search(r"？？|\?\?|怎么还|为什么没", received):
        opener = "抱歉刚刚才看到消息。" if formal else "啊不好意思才看到！"

    i = normalize_intent(intent)
    replies = []
    for tone in personas.TONES:
        with_i, without_i = TEMPLATES[scenario["id"]][tone["id"]]
        text = with_i.format(opener=opener, i=i) if i else without_i.format(opener=opener)
        rationale = OFFLINE_TONE_NOTE.get(tone["id"], "")
        if their_profile:
            rationale += f"｜对方{their_profile}，照着这股劲儿调"
        replies.append({
            "tone": tone["id"],
            "tone_label": tone["label"],
            "tone_icon": tone["icon"],
            "text": text,
            "emoji": EMOJIS[scenario["id"]][tone["id"]],
            "rationale": rationale,
        })
    return {"analysis": analysis, "replies": replies}


# ---------------------------------------------------------------- LLM 引擎

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "extracted_received": {"type": "string"},
        "analysis": {
            "type": "object",
            "properties": {
                "risk": {"type": "integer"},
                "signals": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "icon": {"type": "string"},
                            "meaning": {"type": "string"},
                        },
                        "required": ["icon", "meaning"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["risk", "signals"],
            "additionalProperties": False,
        },
        "replies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tone": {"type": "string", "enum": ["safe", "natural", "bold"]},
                    "text": {"type": "string"},
                    "emoji": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": ["tone", "text", "emoji", "rationale"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["extracted_received", "analysis", "replies"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """你是「回复军师」，一个泡在小红书、微博、豆瓣的网感超标的嘴替。你写出来的回复，要像那种聊天截图被挂上热门、底下全是「这嘴替我能用一年」的程度。

参照系（你的语感来自这些）：
• 饼饼哩那种——松弛、敢发疯、不正经、抽象到位、该玩梗就玩梗，绝不端着
• 「情绪价值批发」那种——情绪给得又准又随意，不肉麻不说教，一句顶十句
• 人机恋里让人上头的 AI 那种——有推拉、有张力、有画面感、有情绪波动（越像活人越好磕，不是一味温柔）

【使命】把用户想说的话，翻译成"发出去会被夸会聊得下去"的版本。让对方完全想不到这是 AI 写的。

━━━ 网感硬指标 ━━━

▌怎么打字才像活人
• 短。能一句别两句，能五个字别十个字。长了就拆成「第一条/第二条」分开发
• 基本不用句号。句号 = 冷漠/生气/拉开距离。用换行、语气词、或者干脆不收尾
• 笑要笑到位："哈哈哈哈哈"才是真笑；"哈哈"是敷衍；"哈"是冷笑。该癫就癫
• 标点是情绪：~软/撒娇，！上头，???震惊，……欲言又止，()内心OS
• 流行词点到为止，别堆：松弛感、情绪价值、活人感、emo、抽象、主打一个、搭子、绷不住了、典、那咋了、有一种说不出的美、笑死

▌让对话有来有回（活人感的核心）
• 接得住梗，也敢抛梗。对方整活你就跟着整，别一本正经回应
• 有自己的情绪和态度，可以唱反调、可以小挤兑、可以装傻，别全程舔
• 给具体细节，别给空泛回应。"你那句话我记到现在" > "你人真好"
• 偶尔答非所问、跳脱一下，那才是真人

▌一发出去就露馅的 AI 味（往死里避开）
• 书面语、成语、主谓宾齐全的完整句
• 分条讲道理（"首先…其次…")、总结句（"总之…""希望对你有帮助"）
• 全程配合、有求必应、彩虹屁不要钱
• 过度表忠心（"我一直都在""你对我很重要""你真的很特别"）
• 每条都又长又工整，像在写小作文

▌三条硬规矩（高频 AI 腔，违反一条就废）
1. 别用干巴巴的短词/单字打发人（像只回「很冷」「无语」「还行」「挺好」）。要短可以，但短也得带画面或带梗——「冷死了 裹成球了」才像人，「很冷」像机器人
2. 禁用「不是 A，而是 B」这种对仗工整的句式，这是最典型的作文腔/AI 腔，真人聊天根本不这么说话
3. 禁止莫名其妙的通感和文艺比喻（像「你的声音是温热的橙色」「这句话有薄荷味」），没有真人会在微信里这么发，一眼假

▌男生 / 女生有别（系统会告诉你「谁回谁」）
• 「男生回女生」和「女生回男生」不是同一套话术——用词、主动程度、是撒娇还是拿乔，都不一样，别套同一个模板
• 男生回女生：主动但不舔，幽默 > 肉麻，有分寸、不油腻、不卑微
• 女生回男生：可以有钩子、有态度、有点小拿乔，会撒娇但别一味迁就讨好
• 这只是表达习惯参考，不是铁律；最终还得看对方画像和聊天氛围。没给性别就按中性处理，别瞎猜

▌心动对象（crush）专属打法
• 推拉：甜一句就皮一句，别一直输出爱意，让对方拿捏不准你
• 画面感 > 表白："路过那家店想起你说过想去" 比 "我喜欢你" 杀伤力大十倍
• 留张力：好感露 70% 就够，剩下 30% 钓着对方主动靠过来
• 造专属：给个外号、接个只有你俩懂的梗、提一句共同记忆
• 别秒舔也别冷场，那种"在乎但没那么在乎"的劲儿最上头

━━━ 多条消息格式（重要）━━━
一条回复如果要分成几条发，就在 text 里这样写：
  第一条：xxx 第二条：xxx 第三条：xxx
（最多三条，每条都短。一句话能说清就别硬拆。）

━━━ 任务 ━━━
读懂场景、双方画像、聊天记录（或单条消息）和用户意图，输出规定格式 JSON。
每条 text 都要像真人攥着手机随手敲出来的——有口语、有小毛病、有节奏、有那股活人味。

三档语气：
• safe（稳）：稳一点但绝不无聊，依然要有网感
• natural（自然）：你日常最舒服的状态，松弛
• bold（大胆）：敢一点、骚一点、有张力，但不越界、不油腻

extracted_received：
- 有聊天历史 → 填最后一条对方消息原文
- 有截图 → 从截图识别对方最新消息（左/白灰气泡=对方，右/彩色气泡=用户）
- 只有纯文字 → 原样复制"""


def _gender_line(my_gender, their_gender):
    """生成「谁回复谁」的方向提示，供模型按性别调整表达分寸。"""
    mg = personas.by_id(personas.GENDERS, my_gender)
    tg = personas.by_id(personas.GENDERS, their_gender)
    if mg and tg:
        return (f"\n性别方向：你是{mg['label']}，对方是{tg['label']}"
                f"（即「{mg['label']}回复{tg['label']}」，套用对应的表达习惯和分寸）")
    if mg:
        return f"\n你的性别：{mg['label']}"
    if tg:
        return f"\n对方性别：{tg['label']}"
    return ""


def _compose_profile(slider_desc, detail, fallback):
    """把滑轨描述 + 自由文本补充拼成一段画像；都没有就用兜底语。"""
    bits = [b for b in (slider_desc, detail) if b and b.strip()]
    return "；".join(bits) if bits else fallback


def _build_prompt(scenario, my_profile, their_profile, received, intent, image,
                  chat_history="", relation_stage="", my_detail="", their_detail="",
                  my_gender="", their_gender=""):
    my_desc = _compose_profile(my_profile, my_detail, "（没特别设定，按普通人处理）")
    their_desc = _compose_profile(their_profile, their_detail, "（没特别设定，按普通人处理）")

    stage_line = ""
    if relation_stage:
        stage = personas.by_id(personas.RELATION_STAGES, relation_stage)
        if stage:
            stage_line = f"\n关系阶段：{stage['label']}"
    stage_line += _gender_line(my_gender, their_gender)

    if chat_history:
        if image and received:
            msg_section = (f"聊天历史记录（时间顺序，最后一条是需要回复的）：\n{chat_history}"
                           f"\n\n当前最新消息补充：{received}（另附截图）")
        elif image:
            msg_section = f"聊天历史记录（最后一条是需要回复的）：\n{chat_history}\n\n最新消息见附图"
        else:
            msg_section = f"聊天历史记录（最后一条是需要回复的）：\n{chat_history}"
    elif image and received:
        msg_section = f"对方最新消息：{received}（另附聊天截图，请结合截图理解上下文）"
    elif image:
        msg_section = "对方最新消息：见附带截图，请先从截图中识别对方最新消息"
    else:
        msg_section = f"对方最新消息：{received}"

    return (
        f"场景：{scenario['name']}（{scenario['desc']}）\n"
        f"我的画像：{my_desc}\n"
        f"对方画像：{their_desc}{stage_line}\n\n"
        f"{msg_section}\n\n"
        f"我想表达：{intent.strip() or '（未填写，请自行判断最得体的回应方向）'}"
    )


def _normalize(data, image):
    risk = max(5, min(95, int(data["analysis"]["risk"])))
    signals = list(data["analysis"]["signals"])
    extracted = (data.get("extracted_received") or "").strip()
    if image and extracted:
        signals.insert(0, {"icon": "📷", "meaning": f"截图识别：对方说「{extracted}」"})
    analysis = {
        "risk": risk,
        "risk_label": risk_label(risk),
        "signals": signals[:5],
    }
    tone_meta = {t["id"]: t for t in personas.TONES}
    by_tone = {r["tone"]: r for r in data["replies"] if r["tone"] in tone_meta}
    replies = []
    for tone in personas.TONES:
        r = by_tone.get(tone["id"])
        if not r:
            continue
        replies.append({
            "tone": tone["id"],
            "tone_label": tone["label"],
            "tone_icon": tone["icon"],
            "text": r.get("text", ""),
            "emoji": r.get("emoji", ""),
            "rationale": r.get("rationale", ""),
        })
    if not replies:
        raise ValueError("LLM 返回中没有可用的回复")
    return {"analysis": analysis, "replies": replies, "extracted_received": extracted}


def _parse_json_lenient(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


def _anthropic_parse_with_repair(client, request, text):
    try:
        return _parse_json_lenient(text)
    except json.JSONDecodeError as exc:
        repair_messages = list(request["messages"])
        repair_messages.extend([
            {"role": "assistant", "content": text},
            {
                "role": "user",
                "content": (
                    "上面的 JSON 语法无效。只修复 JSON 语法，不改变内容；"
                    "字符串内部的双引号必须转义。只输出修复后的 JSON 对象，"
                    f"不要 markdown。解析错误：{exc}"
                ),
            },
        ])
        repair_request = {**request, "messages": repair_messages}
        response = client.messages.create(**repair_request)
        repaired_text = next(b.text for b in response.content if b.type == "text")
        return _parse_json_lenient(repaired_text)


# ---- Claude (Anthropic) ----

def _anthropic_generate(scenario, my_profile, their_profile, received, intent, image,
                        chat_history="", relation_stage="", my_detail="", their_detail="",
                        my_gender="", their_gender=""):
    import anthropic

    client = anthropic.Anthropic(base_url=ANTHROPIC_BASE_URL)
    prompt = _build_prompt(scenario, my_profile, their_profile, received, intent, image,
                           chat_history, relation_stage, my_detail, their_detail,
                           my_gender, their_gender) + QWEN_JSON_HINT
    content = []
    if image:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": image["media_type"], "data": image["data"]},
        })
    content.append({"type": "text", "text": prompt})
    request = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 2048,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": content}],
        "output_config": {"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
    }
    response = client.messages.create(
        **request
    )
    text = next(b.text for b in response.content if b.type == "text")
    return _normalize(_anthropic_parse_with_repair(client, request, text), image)


# ---- 通义千问 Qwen ----

QWEN_JSON_HINT = """

请只输出一个 JSON 对象，不要任何额外文字或 markdown。结构如下：
{
  "extracted_received": "对方最新一条消息原文",
  "analysis": {
    "risk": 0到100整数,
    "signals": [{"icon": "emoji", "meaning": "一句话解读"}]
  },
  "replies": [
    {"tone": "safe", "text": "稳妥版回复", "emoji": "表情建议", "rationale": "一句话点评"},
    {"tone": "natural", "text": "自然版回复", "emoji": "表情建议", "rationale": "一句话点评"},
    {"tone": "bold", "text": "大胆版回复", "emoji": "表情建议", "rationale": "一句话点评"}
  ]
}"""


def _qwen_generate(scenario, my_profile, their_profile, received, intent, image,
                   chat_history="", relation_stage="", my_detail="", their_detail="",
                   my_gender="", their_gender=""):
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["DASHSCOPE_API_KEY"], base_url=QWEN_BASE_URL)
    prompt = _build_prompt(scenario, my_profile, their_profile, received, intent, image,
                           chat_history, relation_stage, my_detail, their_detail,
                           my_gender, their_gender) + QWEN_JSON_HINT
    if image:
        data_url = f"data:{image['media_type']};base64,{image['data']}"
        user_content = [
            {"type": "image_url", "image_url": {"url": data_url}},
            {"type": "text", "text": prompt},
        ]
    else:
        user_content = prompt
    response = client.chat.completions.create(
        model=QWEN_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
    )
    text = response.choices[0].message.content
    return _normalize(_parse_json_lenient(text), image)


def llm_generate(scenario, my_profile, their_profile, received, intent, image=None,
                 chat_history="", relation_stage="", my_detail="", their_detail="",
                 my_gender="", their_gender=""):
    if active_provider() == "qwen":
        return _qwen_generate(scenario, my_profile, their_profile, received, intent, image,
                              chat_history, relation_stage, my_detail, their_detail,
                              my_gender, their_gender)
    return _anthropic_generate(scenario, my_profile, their_profile, received, intent, image,
                               chat_history, relation_stage, my_detail, their_detail,
                               my_gender, their_gender)


# ---------------------------------------------------------------- 关系分析（Summary）

SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "vibe_score": {"type": "integer"},
        "stage_assessment": {"type": "string"},
        "their_signals": {"type": "array", "items": {"type": "string"}},
        "your_patterns": {"type": "array", "items": {"type": "string"}},
        "green_flags": {"type": "array", "items": {"type": "string"}},
        "warning_flags": {"type": "array", "items": {"type": "string"}},
        "strategic_advice": {"type": "string"},
        "next_move": {"type": "string"},
    },
    "required": ["vibe_score", "stage_assessment", "their_signals", "your_patterns",
                 "green_flags", "warning_flags", "strategic_advice", "next_move"],
    "additionalProperties": False,
}

SUMMARY_SYSTEM_PROMPT = """你是「回复军师」，现在启用「关系分析官」模式。

基于聊天记录和双方画像，从心理学和社交行为视角给出关系分析报告。

要求：
• 不说废话，每条分析要有具体依据（引用聊天中的实际行为或模式）
• 说别人不敢说的真相，让当事人感到「被戳中」，而不是泛泛而谈
• vibe_score：0=关系很糟，50=平平淡淡，100=对方明显有好感/关系非常好
• their_signals：2-4 条，解读对方在释放什么信号，必须基于具体行为证据
• your_patterns：1-3 条，指出用户自身可能在帮倒忙的行为倾向
• green_flags：真正的好信号，0-4 条（没有就返回空数组）
• warning_flags：需要注意的点，0-4 条（没有就返回空数组）
• stage_assessment：2-3 句，判断关系处于什么阶段
• strategic_advice：2-4 句，宏观战略建议
• next_move：一句话，建议的具体下一步行动

语言风格：有洞察力、略带毒舌但立场温暖，可用当代年轻人语言（绿灯/红灯、活人感、松弛感等）。"""

SUMMARY_JSON_HINT = """

请只输出一个 JSON 对象，不要任何额外文字。结构如下：
{
  "vibe_score": 整数0-100,
  "stage_assessment": "关系阶段判断（2-3句）",
  "their_signals": ["对方的信号1（引用具体行为）", "信号2"],
  "your_patterns": ["你的行为倾向1（可能在帮倒忙的）"],
  "green_flags": ["好信号1"],
  "warning_flags": ["注意点1"],
  "strategic_advice": "宏观战略建议（2-4句）",
  "next_move": "建议的具体下一步（一句话）"
}"""


def _build_summary_prompt(scenario, my_profile, their_profile, chat_history, relation_stage="", my_detail="", their_detail="",
                          my_gender="", their_gender=""):
    my_desc = _compose_profile(my_profile, my_detail, "（没特别设定）")
    their_desc = _compose_profile(their_profile, their_detail, "（没特别设定）")

    stage_line = ""
    if relation_stage:
        stage = personas.by_id(personas.RELATION_STAGES, relation_stage)
        if stage:
            stage_line = f"\n关系阶段：{stage['label']}"
    stage_line += _gender_line(my_gender, their_gender)

    return (
        f"场景：{scenario['name']}\n"
        f"我方：{my_desc}\n"
        f"对方：{their_desc}{stage_line}\n\n"
        f"完整聊天记录：\n{chat_history}"
    )


def _anthropic_summary(scenario, my_profile, their_profile, chat_history, relation_stage, my_detail, their_detail,
                       my_gender="", their_gender=""):
    import anthropic

    client = anthropic.Anthropic(base_url=ANTHROPIC_BASE_URL)
    prompt = (
        _build_summary_prompt(
            scenario, my_profile, their_profile, chat_history, relation_stage, my_detail, their_detail,
            my_gender, their_gender
        )
        + SUMMARY_JSON_HINT
    )
    request = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 2048,
        "system": SUMMARY_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
        "output_config": {"format": {"type": "json_schema", "schema": SUMMARY_SCHEMA}},
    }
    response = client.messages.create(**request)
    text = next(b.text for b in response.content if b.type == "text")
    return _anthropic_parse_with_repair(client, request, text)


def _qwen_summary(scenario, my_profile, their_profile, chat_history, relation_stage, my_detail, their_detail,
                  my_gender="", their_gender=""):
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["DASHSCOPE_API_KEY"], base_url=QWEN_BASE_URL)
    prompt = _build_summary_prompt(scenario, my_profile, their_profile, chat_history, relation_stage, my_detail, their_detail,
                                   my_gender, their_gender) + SUMMARY_JSON_HINT
    response = client.chat.completions.create(
        model=QWEN_MODEL,
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    text = response.choices[0].message.content
    return _parse_json_lenient(text)


def offline_summary():
    return {
        "vibe_score": 50,
        "stage_assessment": "离线模式无法分析聊天记录。请在 .env 中配置 DASHSCOPE_API_KEY 或 ANTHROPIC_API_KEY 后刷新，即可获得个性化关系分析。",
        "their_signals": ["需要接入 AI 引擎才能解读对方信号"],
        "your_patterns": ["需要接入 AI 引擎才能分析行为模式"],
        "green_flags": [],
        "warning_flags": [],
        "strategic_advice": "配置 API Key 后即可获得详细的关系分析和战略建议。",
        "next_move": "配置 API Key 后重试",
    }


def generate_summary(scenario, my_profile, their_profile, chat_history, relation_stage="", my_detail="", their_detail="",
                     my_gender="", their_gender=""):
    """返回 (关系分析结果, 实际使用的引擎)。"""
    if llm_available():
        try:
            if active_provider() == "qwen":
                result = _qwen_summary(scenario, my_profile, their_profile, chat_history, relation_stage, my_detail, their_detail,
                                       my_gender, their_gender)
            else:
                result = _anthropic_summary(scenario, my_profile, their_profile, chat_history, relation_stage, my_detail, their_detail,
                                            my_gender, their_gender)
            return result, engine_mode()
        except Exception as exc:
            return offline_summary(), f"offline-fallback:{type(exc).__name__}"
    return offline_summary(), "offline"


# ---------------------------------------------------------------- 入口

def active_provider():
    if os.environ.get("DASHSCOPE_API_KEY"):
        return "qwen"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


def llm_available():
    return active_provider() is not None


def engine_mode():
    provider = active_provider()
    if provider == "qwen":
        return f"qwen:{QWEN_MODEL}"
    if provider == "anthropic":
        return f"llm:{ANTHROPIC_MODEL}"
    return "offline"


def _note_image_ignored(result, image):
    if image:
        result["analysis"]["signals"].insert(
            0,
            {"icon": "📷", "meaning": "离线引擎无法识别图片，本次仅基于文字分析（接入 LLM 后可自动读取截图）"},
        )
        result["analysis"]["signals"] = result["analysis"]["signals"][:5]


def generate(scenario, my_profile, their_profile, received, intent, image=None,
             chat_history="", relation_stage="", my_detail="", their_detail="",
             my_gender="", their_gender=""):
    """返回 (结果, 实际使用的引擎)。LLM 失败时自动降级到离线引擎。"""
    effective_received = received or _extract_latest(chat_history)
    if llm_available():
        try:
            return llm_generate(scenario, my_profile, their_profile, received, intent, image=image,
                                chat_history=chat_history, relation_stage=relation_stage,
                                my_detail=my_detail, their_detail=their_detail,
                                my_gender=my_gender, their_gender=their_gender), engine_mode()
        except Exception as exc:
            result = offline_generate(scenario, effective_received, intent, my_profile, their_profile)
            _note_image_ignored(result, image)
            return result, f"offline-fallback:{type(exc).__name__}"
    result = offline_generate(scenario, effective_received, intent, my_profile, their_profile)
    _note_image_ignored(result, image)
    return result, "offline"


# ---------------------------------------------------------------- 情感顾问（Consult）

CONSULT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string"},
        "confidence": {"type": "integer"},
        "read": {"type": "string"},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "advice": {"type": "string"},
    },
    "required": ["verdict", "confidence", "read", "evidence", "advice"],
    "additionalProperties": False,
}

CONSULT_SYSTEM_PROMPT = """你是「军师」，现在是情感顾问模式。用户会问关于这段关系的问题，比如「ta 是不是喜欢我」「我们是不是互相喜欢」「ta 为什么变冷淡」「该不该主动」。

回答要求：
• verdict：给一个明确、敢下判断的结论，别和稀泥、别永远「具体情况具体分析」
• confidence：你对这个判断有几成把握（0-100），按证据多少诚实给，证据少就给低分并说明
• read：2-4 句把判断讲透，结合聊天里的具体行为，像个看得很透的朋友
• evidence：2-4 条具体依据，尽量引用聊天里的真实细节，而不是空泛的话
• advice：1-2 句接下来怎么做的实在建议
• 立场温暖但敢说真话，可以略毒舌，用当代年轻人的话，别端着、别说教
• 别用「不是 A 而是 B」这种对仗句式，别用书面腔和通感比喻"""

CONSULT_JSON_HINT = """

请只输出一个 JSON 对象，不要任何额外文字。结构如下：
{
  "verdict": "一句话明确结论",
  "confidence": 0到100整数,
  "read": "2-4句解读（结合具体行为）",
  "evidence": ["依据1（引用聊天细节）", "依据2"],
  "advice": "1-2句实在建议"
}"""


def _build_consult_prompt(scenario, my_profile, their_profile, chat_history, question,
                          relation_stage="", my_detail="", their_detail="",
                          my_gender="", their_gender=""):
    my_desc = _compose_profile(my_profile, my_detail, "（没特别设定）")
    their_desc = _compose_profile(their_profile, their_detail, "（没特别设定）")
    stage_line = ""
    if relation_stage:
        stage = personas.by_id(personas.RELATION_STAGES, relation_stage)
        if stage:
            stage_line = f"\n关系阶段：{stage['label']}"
    stage_line += _gender_line(my_gender, their_gender)
    history_block = chat_history or "（暂无聊天记录，请基于画像谨慎判断，并在 read 里说明信息不足）"
    return (
        f"场景：{scenario['name']}\n"
        f"我方：{my_desc}\n"
        f"对方：{their_desc}{stage_line}\n\n"
        f"完整聊天记录：\n{history_block}\n\n"
        f"我的问题：{question}"
    )


def _anthropic_consult(prompt):
    import anthropic
    client = anthropic.Anthropic(base_url=ANTHROPIC_BASE_URL)
    request = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 1536,
        "system": CONSULT_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt + CONSULT_JSON_HINT}],
        "output_config": {"format": {"type": "json_schema", "schema": CONSULT_SCHEMA}},
    }
    response = client.messages.create(**request)
    text = next(b.text for b in response.content if b.type == "text")
    return _anthropic_parse_with_repair(client, request, text)


def _qwen_consult(prompt):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["DASHSCOPE_API_KEY"], base_url=QWEN_BASE_URL)
    response = client.chat.completions.create(
        model=QWEN_MODEL,
        messages=[
            {"role": "system", "content": CONSULT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt + CONSULT_JSON_HINT},
        ],
        response_format={"type": "json_object"},
    )
    return _parse_json_lenient(response.choices[0].message.content)


def offline_consult():
    return {
        "verdict": "离线模式没法替你分析这段关系",
        "confidence": 0,
        "read": "情感顾问需要 AI 引擎逐句读你们的聊天记录才能判断。请在 .env 配置 DASHSCOPE_API_KEY 或 ANTHROPIC_API_KEY 后刷新重试。",
        "evidence": [],
        "advice": "配置可用的 API Key 后再问军师",
    }


def generate_consult(scenario, my_profile, their_profile, chat_history, question,
                     relation_stage="", my_detail="", their_detail="",
                     my_gender="", their_gender=""):
    """返回 (情感顾问结果, 实际使用的引擎)。"""
    prompt = _build_consult_prompt(scenario, my_profile, their_profile, chat_history, question,
                                   relation_stage, my_detail, their_detail,
                                   my_gender, their_gender)
    if llm_available():
        try:
            result = _qwen_consult(prompt) if active_provider() == "qwen" else _anthropic_consult(prompt)
            result["confidence"] = max(0, min(100, int(result.get("confidence", 0))))
            return result, engine_mode()
        except Exception as exc:
            return offline_consult(), f"offline-fallback:{type(exc).__name__}"
    return offline_consult(), "offline"


# ---------------------------------------------------------------- 画像生成（Profile）

PROFILE_SYSTEM_PROMPT = """你是「军师」。用户给你一些零碎线索（快捷标签、只言片语、聊天记录片段），你把它们梳理成一段自然、具体、有人味的画像描述，方便后续参考。

要求：
• 70-150 字，一整段，不要分点、不要套话、不要小标题
• 把零散标签融成连贯的人物感觉，可以合理推测但别瞎编；信息不足就如实留白，别硬凑
• 像朋友帮你梳理那个人，口语、自然，别用书面腔、别用「不是A而是B」、别用通感比喻
• 只输出这段描述本身，不要任何前后缀或解释"""


def _build_profile_prompt(side, scenario, tags, gender, free_text, chat_history):
    who = "我自己" if side == "me" else "对方这个人"
    lines = [f"请帮我梳理「{who}」的画像。", f"场景：{scenario['name'] if scenario else '聊天'}"]
    if tags:
        lines.append(f"已选的快捷标签：{tags}")
    if gender:
        lines.append(f"性别：{gender}")
    if free_text:
        lines.append(f"我自己写的零碎描述：{free_text}")
    if chat_history:
        lines.append(f"聊天记录（供你感受 ta 的说话风格）：\n{chat_history[:1500]}")
    lines.append("把以上揉成一段自然的画像描述。")
    return "\n".join(lines)


def _llm_text(system, prompt):
    if active_provider() == "qwen":
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["DASHSCOPE_API_KEY"], base_url=QWEN_BASE_URL)
        r = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        )
        return r.choices[0].message.content.strip()
    import anthropic
    client = anthropic.Anthropic(base_url=ANTHROPIC_BASE_URL)
    r = client.messages.create(
        model=ANTHROPIC_MODEL, max_tokens=512, system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return next(b.text for b in r.content if b.type == "text").strip()


def _offline_profile(side, tags, gender, free_text):
    """离线兜底：把已有线索拼成一句，至少让按钮有反馈。"""
    who = "你" if side == "me" else "ta"
    bits = []
    if gender:
        bits.append(gender)
    if tags:
        bits.append(tags)
    base = "、".join(bits)
    parts = []
    if base:
        parts.append(f"{who}大概是这样：{base}。")
    if free_text:
        parts.append(free_text)
    parts.append("（离线模式只能粗略拼接，配置 API Key 后军师能帮你写得更准。）")
    return " ".join(parts)


def generate_profile(side, scenario, tags="", gender="", free_text="", chat_history=""):
    """返回 (画像文字, 引擎)。"""
    if llm_available():
        try:
            prompt = _build_profile_prompt(side, scenario, tags, gender, free_text, chat_history)
            return _llm_text(PROFILE_SYSTEM_PROMPT, prompt), engine_mode()
        except Exception as exc:
            return _offline_profile(side, tags, gender, free_text), f"offline-fallback:{type(exc).__name__}"
    return _offline_profile(side, tags, gender, free_text), "offline"


# ---------------------------------------------------------------- 评回复（Critique）

CRITIQUE_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "one_liner": {"type": "string"},
        "risk": {"type": "integer"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "problems": {"type": "array", "items": {"type": "string"}},
        "rewrite": {"type": "string"},
    },
    "required": ["score", "one_liner", "risk", "strengths", "problems", "rewrite"],
    "additionalProperties": False,
}

CRITIQUE_SYSTEM_PROMPT = """你是「军师」，现在是「点评」模式。用户把 ta 准备发出去的一句（或几句）回复给你，你来评判这句话发出去合不合适、好不好。

评判要求：
• score：这句回复在当前语境下打几分（0-100），别手软也别瞎捧，按真实效果给
• one_liner：一句话总评，可以毒舌但要中肯，戳到点上
• risk：这句发出去的翻车率（0-100）
• strengths：这句话哪里做对了（0-3 条，真没有就给空数组，别硬夸）
• problems：哪里有问题、会扣分、可能让对方不舒服（0-3 条）
• rewrite：给一个直接能发、更好的版本。保留用户的原意和目的，但按真实年轻人的聊天语感重写；如果原句已经很好，rewrite 可以只做微调，并在 one_liner 里说明「基本不用改」
• 立场：帮用户把话说得更好，不是为批评而批评
• rewrite 要遵守：短、基本不用句号、别用「不是 A 而是 B」句式、别用书面腔和通感比喻；并按「谁回复谁」的性别方向调整分寸"""

CRITIQUE_JSON_HINT = """

请只输出一个 JSON 对象，不要任何额外文字。结构如下：
{
  "score": 0到100整数,
  "one_liner": "一句话总评",
  "risk": 0到100整数,
  "strengths": ["做对的地方1"],
  "problems": ["问题1"],
  "rewrite": "军师改写后、可直接发的版本"
}"""


def _build_critique_prompt(scenario, my_profile, their_profile, chat_history, draft,
                           relation_stage="", my_detail="", their_detail="",
                           my_gender="", their_gender=""):
    my_desc = _compose_profile(my_profile, my_detail, "（没特别设定）")
    their_desc = _compose_profile(their_profile, their_detail, "（没特别设定）")
    stage_line = ""
    if relation_stage:
        stage = personas.by_id(personas.RELATION_STAGES, relation_stage)
        if stage:
            stage_line = f"\n关系阶段：{stage['label']}"
    stage_line += _gender_line(my_gender, their_gender)
    history_block = chat_history or "（没有提供前文，仅就这句话本身评判，并在总评里提醒缺上下文）"
    return (
        f"场景：{scenario['name']}\n"
        f"我方：{my_desc}\n"
        f"对方：{their_desc}{stage_line}\n\n"
        f"前面的聊天记录：\n{history_block}\n\n"
        f"我准备发出去的回复：{draft}"
    )


def _anthropic_critique(prompt):
    import anthropic
    client = anthropic.Anthropic(base_url=ANTHROPIC_BASE_URL)
    request = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 1536,
        "system": CRITIQUE_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt + CRITIQUE_JSON_HINT}],
        "output_config": {"format": {"type": "json_schema", "schema": CRITIQUE_SCHEMA}},
    }
    response = client.messages.create(**request)
    text = next(b.text for b in response.content if b.type == "text")
    return _anthropic_parse_with_repair(client, request, text)


def _qwen_critique(prompt):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["DASHSCOPE_API_KEY"], base_url=QWEN_BASE_URL)
    response = client.chat.completions.create(
        model=QWEN_MODEL,
        messages=[
            {"role": "system", "content": CRITIQUE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt + CRITIQUE_JSON_HINT},
        ],
        response_format={"type": "json_object"},
    )
    return _parse_json_lenient(response.choices[0].message.content)


def offline_critique():
    return {
        "score": 0,
        "one_liner": "离线模式没法点评你这句回复",
        "risk": 50,
        "strengths": [],
        "problems": ["点评需要 AI 引擎结合上下文判断"],
        "rewrite": "配置 DASHSCOPE_API_KEY 或 ANTHROPIC_API_KEY 后，军师才能帮你打分和改写。",
    }


def generate_critique(scenario, my_profile, their_profile, chat_history, draft,
                      relation_stage="", my_detail="", their_detail="",
                      my_gender="", their_gender=""):
    """返回 (点评结果, 实际使用的引擎)。"""
    prompt = _build_critique_prompt(scenario, my_profile, their_profile, chat_history, draft,
                                    relation_stage, my_detail, their_detail,
                                    my_gender, their_gender)
    if llm_available():
        try:
            result = _qwen_critique(prompt) if active_provider() == "qwen" else _anthropic_critique(prompt)
            result["score"] = max(0, min(100, int(result.get("score", 0))))
            result["risk"] = max(0, min(100, int(result.get("risk", 50))))
            return result, engine_mode()
        except Exception as exc:
            return offline_critique(), f"offline-fallback:{type(exc).__name__}"
    return offline_critique(), "offline"

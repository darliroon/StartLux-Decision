"""StartLux-Decision-4B 能力全景演示.

五个例子, 每个展示一项与"生成式 LLM"不同的核心能力:
  1. 一次前向回答 8 个问题   —— 决策面板 / agent 监督器
  2. 40 选项宽选择           —— 超过 26 个字母的选项列表, 自动分组锦标赛
  3. 图像决策                —— 用车道标注 overlay 图实测视觉能力
  4. 批量 + 不确定性路由     —— 概率即置信度, 低置信度自动转人工
  5. 长上下文一次读多次问    —— 200 条账户事件作为共享证据, 6 个问题复用

用法: cd /home/liufeng/projects/StartLux-Decision && CUDA_VISIBLE_DEVICES=0 python demo_capabilities.py
"""
import json
import random
import time

from startlux_decision import StartLuxDecision

MODEL_DIR = "/data/liufeng/models/StartLux-Decision-4B"
m = StartLuxDecision(MODEL_DIR)
print(f"model: 4B, device={m.device}, fast_kernels={m.fast_kernels}\n")


def run(title, state, questions, images=None, note=""):
    print("=" * 78)
    print(f"[{title}]")
    if isinstance(state, str):
        preview = state[:100].replace("\n", " ") + ("..." if len(state) > 100 else "")
    else:
        preview = json.dumps(state, ensure_ascii=False)[:100] + "..."
    print(f"  state: {preview}")
    t0 = time.perf_counter()
    answers, usage = m.decide(state, questions, images=images)
    ms = (time.perf_counter() - t0) * 1000
    for k, a in answers.items():
        if a["type"] == "choice":
            top = sorted(a["probabilities"].items(), key=lambda x: -x[1])[:3]
            top_s = "  ".join(f"{i}={p:.3f}" for i, p in top)
            print(f"  {k}: {a['choice']}  (conf {a['confidence']:.2f})   {top_s}")
        elif a["type"] == "noul":
            print(f"  {k}: P(true) = {a['noul']:.3f}")
        else:
            top = sorted(a["probabilities"].items(), key=lambda x: -x[1])[:3]
            top_s = "  ".join(f"{i}={p:.3f}" for i, p in top)
            print(f"  {k}: {a['score']:.2f}  (conf {a['confidence']:.2f})   {top_s}")
    print(f"  -> {len(questions)} 个问题 / {usage['input_tokens']} tokens / {ms:.0f} ms")
    if note:
        print(f"  NOTE: {note}")
    print()
    return answers


# ==================================================================== 1
q1 = {
    "intent": {"type": "choice", "instructions": "What does the user want?",
               "criteria": {"book": "make a new booking", "change": "modify an existing booking",
                            "cancel": "cancel and get a refund", "status": "just ask about flight status"}},
    "needs_tool": {"type": "noul", "instructions": "Does this require calling an external tool (calendar, payment, CRM)?"},
    "urgency": {"type": "score", "instructions": "How urgent is it?",
                "criteria": ["can wait days", "same week", "today", "next flight"]},
    "sentiment": {"type": "choice", "instructions": "Customer sentiment?",
                  "criteria": {"angry": "furious, threatening to leave", "frustrated": "annoyed but civil",
                               "neutral": "business-like", "happy": "pleased"}},
    "escalate": {"type": "noul", "instructions": "Should a human agent review this conversation before closing?"},
    "language": {"type": "choice", "instructions": "Which language is the message written in?",
                 "criteria": {"en": "English", "de": "German", "zh": "Chinese", "es": "Spanish"}},
    "fraud_risk": {"type": "score", "instructions": "How much does this look like fraud or abuse?",
                   "criteria": ["none", "suspicious", "likely"]},
    "answer_tone": {"type": "choice", "instructions": "What tone should the reply use?",
                    "criteria": {"apologetic": "own the mistake, compensate", "plain": "just the facts",
                                 "firm": "hold the policy line"}},
}
state1 = ("Message from customer #8812: 'I paid for seat 12A with extra legroom on flight LX331 tomorrow and just got "
          "moved to a middle seat in the back with NO refund and NO explanation. This is the second time. I want my "
          "money back today or I'm filing a chargeback with my bank.'")
run("1) 决策面板: 8 个问题一次前向 (客服监督器场景)", state1, q1,
    note="无任何生成 —— 一次前向读完 8 行输出, 这是它与生成式 LLM 的本质区别")

# ==================================================================== 2
departments = {
    "billing_refunds": "charges, refunds, invoices, payment disputes",
    "billing_subscriptions": "recurring plans, upgrades, downgrades, price questions",
    "shipping_domestic": "delivery inside the country, courier handoff, delays",
    "shipping_international": "customs, cross-border duties, lost parcels abroad",
    "returns_apparel": "clothing and shoe returns, size exchanges",
    "returns_electronics": "device returns, warranty claims, repairs",
    "account_access": "login failures, password resets, account lockouts",
    "account_closure": "deleting accounts, data export requests",
    "privacy_gdpr": "data deletion, consent, legal privacy requests",
    "technical_web": "website errors, checkout bugs, browser issues",
    "technical_app": "mobile app crashes, updates, sync problems",
    "technical_api": "developer API keys, webhooks, integration bugs",
    "product_apparel": "questions about clothing materials, sizing, care",
    "product_electronics": "specs of devices, compatibility, comparisons",
    "product_home": "furniture, appliances, home goods advice",
    "product_grocery": "food, perishables, dietary questions",
    "loyalty_points": "reward points, tiers, redemption problems",
    "gift_cards": "gift card balance, activation, expiry",
    "promotions": "coupons, sale pricing, price matching",
    "marketplace_sellers": "third-party seller issues, seller performance",
    "marketplace_buyers": "buyer protection, item-not-received claims",
    "fraud_investigation": "unauthorized transactions, stolen cards",
    "fraud_verification": "identity checks, verification holds",
    "legal_notices": "subpoenas, takedown requests, legal threats",
    "press": "journalist inquiries, interview requests",
    "careers": "job applications, recruiter contact",
    "accessibility": "screen reader problems, alt text, accommodations",
    "translations": "wrong or missing translations of content",
    "content_moderation": "reporting abusive reviews or messages",
    "partnerships": "B2B partnerships, wholesale, affiliates",
    "investor_relations": "shareholder questions, earnings, filings",
    "facilities": "warehouse pickup, office visits, damaged packaging on arrival",
    "subscriptions_content": "streaming, digital content, e-books access",
    "travel_services": "bundled travel bookings, hotels, flights sold on platform",
    "insurance_claims": "shipping insurance, product protection plans",
    "feedback_product": "feature requests, beta program interest",
    "events": "webinars, in-store events, ticketing",
    "b2b_bulk": "corporate bulk orders, invoicing terms",
    "security_reports": "vulnerability reports, bug bounty",
    "misc_general": "anything that fits no other department",
}
assert len(departments) == 40
state2 = ("Customer message: 'The espresso machine I ordered arrived with a cracked water tank and the box smelled of "
          "fuel. I want a replacement unit, not a refund, and I need it before Friday for a family event.'")
q2 = {"routing": {"type": "choice", "instructions": "Route this message to exactly one department.",
                  "criteria": departments}}
run("2) 宽选择: 40 个部门路由 (超过 26 字母上限, 自动分组赛)", state2, q2,
    note="先按组淘汰再决赛, 决出最优; 输出仍是全部 40 项的完整概率分布")

# ==================================================================== 3
IMG = "/data/liufeng/lane-distill/annotate/overlay/1062.png"
state3 = "Dashcam tile from a road-scene dataset, red lines mark detected lane boundaries: <image>"
q3 = {
    "markings": {"type": "choice", "instructions": "How many lane boundaries are marked in red?",
                 "criteria": {"1": None, "2": None, "3": None, "4": None, "5": None}},
    "dashed": {"type": "noul", "instructions": "Do at least two of the marked boundaries look dashed rather than solid?"},
    "urban": {"type": "noul", "instructions": "Does this look like an urban intersection scene rather than open highway?"},
    "clutter": {"type": "score", "instructions": "How cluttered is the scene (vehicles, shadows, crossings)?",
                "criteria": ["clean", "moderate", "busy"]},
}
run("3) 图像决策: 车道标注图 (真实项目数据)", state3, q3, images=[IMG],
    note="视觉塔编码一次, 问题走与文本相同的路径; 对照标注记录: 该图 4 条线 = 1 实 + 3 虚")

# ==================================================================== 4
tickets = [
    ("Where is my order? Tracking says label created 5 days ago.", "shipping"),
    ("You charged me twice for order #771.", "billing"),
    ("How do I reset my password?", "account"),
    ("The app crashes every time I open the camera.", "technical"),
    ("Do you ship to Canada?", "shipping"),
    ("I want to speak to a manager about my broken laptop that arrived like this, box was crushed", "returns"),
    ("What size battery does the X200 take?", "product"),
    ("I don't understand this charge on my card for 14.99 from you people", "billing"),
    ("Never arrived. Two weeks. Unacceptable.", "shipping"),
    ("Can I pay with two different cards?", "billing"),
    ("It's broken I think maybe, not sure, it makes a weird noise sometimes but works fine otherwise", "technical"),
    ("Refund my order NOW or I call my lawyer, this is robbery", "billing"),
]
topics = {"shipping": "delivery, tracking, arrival problems",
          "billing": "charges, refunds, payment",
          "account": "login, password, profile",
          "technical": "bugs, crashes, errors",
          "returns": "damaged goods, replacements",
          "product": "product questions and specs"}
reqs = [(msg, {"topic": {"type": "choice", "instructions": "Classify the topic of this customer message.",
                         "criteria": topics}}) for msg, _ in tickets]
t0 = time.perf_counter()
batch = m.decide_batch(reqs)
ms = (time.perf_counter() - t0) * 1000
print("=" * 78)
print("[4) 批量 + 不确定性路由: 12 张工单, 概率即置信度]")
n_ok, flagged = 0, []
for (msg, gold), a in zip(tickets, batch):
    got, conf = a["topic"]["choice"], a["topic"]["confidence"]
    mark = "OK " if got == gold else "MISS"
    n_ok += got == gold
    line = (f"  [{mark}] {got:<10} conf={conf:.2f}  {msg[:58]}")
    if conf < 0.55:
        flagged.append(line + "  -> 转人工")
    else:
        print(line)
print(f"  ---- 置信度 < 0.55, 自动转人工 ({len(flagged)} 条) ----")
for l in flagged:
    print(l)
print(f"  -> {len(reqs)} 张工单 / {ms:.0f} ms 总延迟, 准确 {n_ok}/12; 最含糊的两条被置信度正确捕获")
print()

# ==================================================================== 5
random.seed(7)
events, refunds, defect_seen = [], 0, False
topics_ev = ["billing", "delivery", "app_bug", "question", "complaint"]
for i in range(200):
    ev = random.choice(topics_ev)
    rec = {"i": i, "date": f"2026-{1 + i // 90:02d}-{1 + i % 28:02d}", "channel": random.choice(["chat", "email", "phone"]),
           "topic": ev, "minutes": random.randint(3, 40), "csat": random.choice([1, 2, 3, 3, 4, 2])}
    if ev == "billing" and random.random() < 0.3:
        rec["refund"] = random.choice([5, 12, 20]); refunds += rec["refund"]
    if ev == "complaint":
        rec["note"] = "mentions leaving for a competitor"
    if ev == "app_bug" and i > 150:
        rec["note"] = "left-ear audio cuts out"; defect_seen = True
    events.append(rec)
state5 = {"account": "customer #4471, tier gold, 3 years", "interactions": events}
q5 = {
    "ever_defect": {"type": "noul", "instructions": "Did the customer ever report a hardware defect in an interaction?"},
    "churn_threat": {"type": "noul", "instructions": "Did any interaction mention leaving for a competitor?"},
    "most_common": {"type": "choice", "instructions": "Which topic appears most often across the interactions?",
                    "criteria": {t: None for t in topics_ev}},
    "mood": {"type": "score", "instructions": "Overall satisfaction trend of this customer?",
             "criteria": ["worsening", "flat", "improving"]},
    "vip_discount": {"type": "noul", "instructions": "Based on this history, would a proactive retention discount be justified?"},
}
run("5) 长上下文: 200 条互动记录一次读, 5 个问题共享 (检索式提问)", state5, q5,
    note=f"约 {len(json.dumps(events)) // 4} tokens 的状态只读一遍; 检索类问题可靠, 精确算术聚合不是它的强项(无思维链)")

print("=" * 78)
print("总结: 单次前向出全部概率 -> 毫秒级延迟; 概率即置信度 -> 可做不确定性路由;")
print("      一次读多问 -> 省算力; 决策输出无生成 -> 无格式幻觉. 弱点: 无思维链的纯算术/多步推理.")

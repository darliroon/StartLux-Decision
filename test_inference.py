"""StartLux-Decision-4B 推理冒烟测试: 三种问题类型 + 延迟统计.

用法:
    cd /home/liufeng/projects/StartLux-Decision
    CUDA_VISIBLE_DEVICES=0 python test_inference.py
"""
import json
import sys
import time

from startlux_decision import StartLuxDecision

MODEL_DIR = "/data/liufeng/models/StartLux-Decision-4B"


def show(title, state, questions):
    print("=" * 72)
    print(f"[{title}]")
    print(f"state: {json.dumps(state, ensure_ascii=False)[:120]}")
    t0 = time.perf_counter()
    answers, usage = m.decide(state, questions)
    ms = (time.perf_counter() - t0) * 1000
    for k, a in answers.items():
        if a["type"] == "choice":
            probs = {i: f"{p:.3f}" for i, p in a["probabilities"].items()}
            print(f"  {k}: choice = {a['choice']:<10} conf = {a['confidence']:.3f}  probs = {probs}")
        elif a["type"] == "noul":
            print(f"  {k}: P(true) = {a['noul']:.3f}")
        else:
            probs = {i: f"{p:.3f}" for i, p in a["probabilities"].items()}
            print(f"  {k}: score = {a['score']:.2f}  legend = {a['legend']}  probs = {probs}")
    print(f"  tokens={usage['input_tokens']}  latency={ms:.1f} ms")
    return ms


m = StartLuxDecision(MODEL_DIR)
print(f"model loaded from {MODEL_DIR}, device={m.device}, fast_kernels={m.fast_kernels}\n")

# --- 用例 1: 客服工单分派 (README 示例, 一次请求同时问 choice/noul/score 三种问题) ---
state1 = {"ticket": "I was charged twice for order #4411 and the app still shows it as unpaid.",
          "customer_tier": "free", "age_hours": 3}
q1 = {
    "team": {"type": "choice", "instructions": "Which team should handle this ticket?",
             "criteria": {"billing": "Payments, refunds and invoices",
                          "shipping": "Delivery and tracking",
                          "technical": "App, login and account problems"}},
    "urgent": {"type": "noul", "instructions": "Should this ticket be answered today?"},
    "severity": {"type": "score", "instructions": "How severe is the impact?",
                 "criteria": ["cosmetic", "annoying", "blocks the customer"]},
}
ms_cold = show("客服工单分派 (首次, 含内核 JIT 编译)", state1, q1)
show("客服工单分派 (复跑, CUDA graph 生效)", state1, q1)

# --- 用例 2: 数学推理 (GSM8K 风格单选) ---
state2 = "A bakery sold 45 croissants in the morning. In the afternoon it sold 13 fewer croissants than in the morning. How many croissants were sold in total?"
q2 = {"total": {"type": "choice", "instructions": "How many croissants were sold in total?",
                "criteria": {"77": None, "71": None, "90": None, "58": None}}}
show("GSM8K 风格数学题", state2, q2)

# --- 用例 3: 语言理解 (情绪分类) ---
state3 = "Review: 'The headphones arrived on time, but the left ear stopped working after two days. Support never replied to my email.'"
q3 = {"sentiment": {"type": "choice", "instructions": "What is the sentiment of this review?",
                    "criteria": {"positive": "satisfied customer",
                                 "neutral": "mixed or factual",
                                 "negative": "dissatisfied customer"}},
      "mentions_defect": {"type": "noul", "instructions": "Does the review report a product defect?"}}
show("评论情绪分类", state3, q3)

# --- 用例 4: 批量推理 (decide_batch) ---
reqs = [(f"Customer order #{i} was delivered to the wrong address in city {(i * 7) % 20}.",
         {"refund": {"type": "noul", "instructions": "Should the customer get a refund?"}}) for i in range(8)]
t0 = time.perf_counter()
batch = m.decide_batch(reqs)
ms = (time.perf_counter() - t0) * 1000
print("=" * 72)
print(f"[批量推理] {len(reqs)} 个请求 (decide_batch), 总延迟 {ms:.1f} ms")
for (s, _), a in zip(reqs, batch):
    print(f"  {s[:60]}...  -> P(refund) = {a['refund']['noul']:.3f}")

print(f"\n首次请求含 JIT 编译耗时 {ms_cold:.0f} ms; 单请求后续延迟约 20-60 ms 量级 (4B, 3090)")

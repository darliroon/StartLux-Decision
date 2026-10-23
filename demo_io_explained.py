"""把 StartLux-Decision 的输入/输出彻底扒开看.

展示三层:
  第一层: 你传给 decide() 的 Python 参数 (输入)
  第二层: 内部把参数渲染成的实际 prompt (模型真正"读"到的文本)
  第三层: decide() 返回的 Python 对象 (输出)
"""
import json

from startlux_decision import StartLuxDecision
from startlux_decision import jevfmt as J

m = StartLuxDecision("/data/liufeng/models/StartLux-Decision-4B")

# ================= 第一层: 你的输入 =================
state = {"review": "Battery died after 3 weeks, but support replaced it free of charge.",
         "price": 29.99}

questions = {
    "sentiment": {                                        # "sentiment" 是你起的 key
        "type": "choice",                                 # 三种类型: choice / noul / score
        "instructions": "What is the sentiment of this review?",
        "criteria": {                                     # criteria = 候选选项表
            "positive": "the customer is satisfied",
            "negative": "the customer is dissatisfied",
        }},
    "worth_buying": {
        "type": "noul",                                    # noul = 是否题
        "instructions": "Is this product still worth buying despite the defect?",
    },
    "quality": {
        "type": "score",                                  # score = 等级打分
        "instructions": "Rate the product quality.",
        "criteria": ["poor", "average", "good"],         # 从低到高的等级
    },
}

print("=" * 70)
print("第一层  你传入的参数 (纯 Python dict, 没有任何技巧):")
print("=" * 70)
print("state    =", json.dumps(state, ensure_ascii=False))
print("questions=", json.dumps(questions, ensure_ascii=False, indent=1))

# ================= 第二层: 内部渲染的 prompt =================
print()
print("=" * 70)
print("第二层  内部渲染出的 prompt (模型实际读到的全部文本):")
print("=" * 70)
for key, q in questions.items():
    row = J.from_systemone(state, q, qid=key)
    msgs, order = J.messages(row)
    text = m.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True,
                                     enable_thinking=False)
    print(f"\n----- 问题 '{key}' 的 prompt -----")
    print(text)
    print(f"(共 {len(m.tok.encode(text))} 个 token; 答案将在 'ительный' 前的位置读取: A/B/C/D 的 logits)")

# ================= 第三层: 模型输出 =================
answers, usage = m.decide(state, questions)

print()
print("=" * 70)
print("第三层  decide() 的返回值 (每个问题一个结构化答案):")
print("=" * 70)
print(json.dumps(answers, ensure_ascii=False, indent=2))
print()
print("usage =", usage)
print()
print("解读:")
print("  sentiment -> {'choice': 'positive', 'confidence': 0.xx,")
print("                 'probabilities': {'positive': 0.xx, 'negative': 0.xx}}")
print("  worth_buying -> {'noul': 0.xx}        # 就是 P(true) 的值")
print("  quality -> {'score': 1.xx, ...}       # 按等级概率加权的期望分 0..2")

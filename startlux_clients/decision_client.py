#!/usr/bin/env python3
"""访问本机 StartLux-Decision 服务的最小客户端（纯标准库，无需激活任何 conda 环境）。

用法:
  # 1) 直接运行内置 demo（三种题型各一个）
  python decision_client.py

  # 2) 只传一段文本证据，问一个是/否题
  python decision_client.py --state "The app crashes when opening the camera." \
      --question "Is this a technical bug report?" --type noul

  # 3) 用自己的 JSON 请求文件（最灵活，文件内容就是一个完整请求体）
  python decision_client.py --file my_request.json

  # 4) 指定别的服务地址
  python decision_client.py --url http://localhost:8090
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_URL = os.environ.get("STARTLUX_URL", "http://localhost:8095")
ENDPOINT = "/v1/systemone"


def decide(url, body, timeout=300, api_key=None):
    """发送一个决策请求，返回解析后的 JSON dict。"""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    req = urllib.request.Request(
        url.rstrip("/") + ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise SystemExit(f"HTTP {e.code} 错误: {detail}") from e


def pretty_print(result):
    """把返回结果按题型友好地打印出来。"""
    answers = result.get("answers", {})
    for name, ans in answers.items():
        t = ans.get("type")
        if t == "choice":
            probs = ans.get("probabilities", {})
            top = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
            ranked = ", ".join(f"{k}={v:.3f}" for k, v in top)
            print(f"[{name}] choice(单选) -> {ans.get('choice')}  "
                  f"confidence={ans.get('confidence', 0):.3f}")
            print(f"        概率: {ranked}")
            if ans.get("none_probability") is not None:
                print(f"        none_probability(无合适选项)={ans['none_probability']:.3f}"
                      f"  {'⚠️ >=0.2 建议复查' if ans['none_probability'] >= 0.2 else ''}")
        elif t == "noul":
            print(f"[{name}] noul(是/否) -> P(yes)={ans.get('noul', 0):.3f}")
        elif t == "score":
            probs = ans.get("probabilities", {})
            ranked = ", ".join(f"L{k}={v:.3f}" for k, v in sorted(probs.items()))
            legend = ans.get("legend", {})
            print(f"[{name}] score(等级) -> 期望等级={ans.get('score', 0):.3f} / {len(legend) - 1}")
            print(f"        各级概率: {ranked}")
            if legend:
                print("        等级含义: " + "; ".join(f"{k}={v}" for k, v in legend.items()))
        print()
    usage = result.get("usage")
    if usage:
        print(f"usage: 输入 {usage.get('input_tokens')} tokens, 生成 {usage.get('output_tokens')} tokens "
              f"(Instant 单遍判断，生成恒为 0)")


def build_simple_body(state, question, qtype):
    """根据命令行参数构造一个最简单的请求（noul 是/否题；choice/score 需要更复杂结构，请用 --file）。"""
    if qtype != "noul":
        sys.exit("--question 快速模式仅支持 noul(是/否) 题；choice/score 请用 --file 传完整 JSON。")
    return {"state": state, "questions": {"q": {"type": "noul", "instructions": question}}}


DEMO_BODY = {
    "state": {
        "ticket": "I was charged twice for order #4411 and the app still shows it as unpaid."
    },
    "questions": {
        # 单选题：criteria 是 {选项id: 选项描述}
        "team": {
            "type": "choice",
            "instructions": "Which team should handle this ticket?",
            "criteria": {
                "billing": "Payments and refunds",
                "shipping": "Delivery",
                "technical": "App and login",
            },
        },
        # 是/否题：不需要 criteria，返回的 noul 即 P(yes)
        "urgent": {"type": "noul", "instructions": "Should this ticket be answered today?"},
        # 等级题：criteria 是数组，必须从低到高
        "severity": {
            "type": "score",
            "instructions": "How severe is the impact?",
            "criteria": ["cosmetic", "annoying", "blocks the customer"],
        },
    },
}


def main():
    ap = argparse.ArgumentParser(description="StartLux-Decision 服务客户端")
    ap.add_argument("--url", default=DEFAULT_URL, help=f"服务地址（默认 {DEFAULT_URL}）")
    ap.add_argument("--file", help="完整请求体 JSON 文件路径（内容即一个请求 body）")
    ap.add_argument("--state", help="文本证据（配合 --question 的快速模式）")
    ap.add_argument("--question", help="是/否问题（配合 --state）")
    ap.add_argument("--type", default="noul", choices=["noul"], help="快速模式题型（目前仅 noul）")
    ap.add_argument("--raw", action="store_true", help="直接打印原始 JSON，不做友好格式化")
    args = ap.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            body = json.load(f)
    elif args.state and args.question:
        body = build_simple_body(args.state, args.question, args.type)
    elif args.state or args.question:
        sys.exit("--state 和 --question 必须一起提供")
    else:
        print(">>> 未提供参数，运行内置 demo（三种题型）\n")
        body = DEMO_BODY

    result = decide(args.url, body, api_key=os.environ.get("STARTLUX_API_KEY"))
    if args.raw:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        pretty_print(result)


if __name__ == "__main__":
    main()

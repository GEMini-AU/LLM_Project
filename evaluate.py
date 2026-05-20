"""
评估脚本 — 读取实验结果 JSON，从多个维度分析四种策略的表现
"""

import json
import sys
from collections import defaultdict


def load_results(filename: str) -> dict:
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_strategy_stats(data: dict):
    """按策略统计基本信息"""
    results = data["results"]
    stats = defaultdict(lambda: {"count": 0, "avg_latency": 0.0, "avg_response_len": 0})

    for r in results:
        s = stats[r["strategy"]]
        s["count"] += 1
        s["avg_latency"] += r["latency_seconds"]
        s["avg_response_len"] += len(r["response"])

    print("=" * 70)
    print("各策略平均指标")
    print("-" * 70)
    print(f"{'策略':<12} {'题数':<6} {'平均延迟(s)':<12} {'平均响应长度(字符)':<20}")
    print("-" * 70)

    for name in ["Direct", "RaR", "CoT", "RaR+CoT"]:
        s = stats[name]
        n = s["count"]
        if n > 0:
            print(
                f"{name:<12} {n:<6} {s['avg_latency']/n:<12.2f} {s['avg_response_len']/n:<20.0f}"
            )

    print("=" * 70)


def analyze_by_ambiguity_type(data: dict):
    """按歧义类型分组展示"""
    results = data["results"]
    by_type = defaultdict(list)
    for r in results:
        by_type[r["ambiguity_type"]].append(r)

    print("\n按歧义类型分组（仅展示 RaR 与 RaR+CoT 的第一题重述效果）\n")

    for atype in sorted(by_type):
        print(f"--- {atype} ---")
        items = [r for r in by_type[atype] if r["strategy"] in ("RaR", "RaR+CoT")]
        for r in items:
            response_preview = r["response"][:300].replace("\n", "\\n")
            print(f"  [{r['strategy']}] Q{r['question_id']}: {response_preview}...")
            print()
        print()


def extract_rar_sections(data: dict):
    """提取所有 RaR 策略的【重述问题】部分，便于对比重述质量"""
    results = data["results"]

    print("=" * 70)
    print("RaR 重述问题 对比 — 原始问题 vs 重述后的问题")
    print("=" * 70)

    for r in results:
        if r["strategy"] not in ("RaR", "RaR+CoT"):
            continue

        response = r["response"]
        # 尝试提取【重述问题】部分
        rephrase = ""
        for tag in ["【重述问题】", "[重述问题]", "【重述问题】："]:
            idx = response.find(tag)
            if idx != -1:
                rest = response[idx + len(tag):]
                for end_tag in ["【", "["]:
                    end_idx = rest.find(end_tag)
                    if end_idx != -1:
                        rephrase = rest[:end_idx].strip()
                        break
                if not rephrase:
                    rephrase = rest[:200].strip()
                break

        if not rephrase:
            rephrase = "(未能解析重述部分，见完整响应)"

        print(f"\nQ{r['question_id']} [{r['strategy']}] [{r['ambiguity_type']}]")
        print(f"  原始问题: {r['question']}")
        print(f"  重述问题: {rephrase[:300]}")
        print(f"  歧义说明: {r['ambiguity_desc'][:100]}")
        print("-" * 70)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python evaluate.py <results_xxx.json>")
        sys.exit(1)

    filename = sys.argv[1]
    data = load_results(filename)

    print(f"模型: {data['metadata']['model']}")
    print(f"时间: {data['metadata']['timestamp']}")
    print(f"题目数: {data['metadata']['total_questions']}")

    analyze_strategy_stats(data)
    extract_rar_sections(data)
    analyze_by_ambiguity_type(data)

    print("\n" + "=" * 70)
    print("提示: 上述结果用于人工评估。建议从以下维度打分(1-5)：")
    print("  1. 重述是否准确捕捉了原始问题的歧义？")
    print("  2. 重述后的问题是否更具体、更可回答？")
    print("  3. 最终回答是否优于直接回答？")
    print("  4. 重述是否引入了新的偏差或错误？")
    print("=" * 70)

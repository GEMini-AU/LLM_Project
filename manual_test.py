"""
手动测试工具 — 不使用 API，直接在终端查看四种策略的完整 prompt
复制到任何 LLM 对话框中即可手动测试
"""

from prompts import DIRECT_PROMPT, RAR_PROMPT, COT_PROMPT, RAR_COT_PROMPT
from test_set import TEST_QUESTIONS


def preview_all():
    """预览所有题目 × 策略的 prompt"""
    for q in TEST_QUESTIONS:
        print("=" * 80)
        print(f"Q{q['id']} | 类型: {q['ambiguity_type']}")
        print(f"歧义: {q['ambiguity_desc'][:150]}")
        print(f"问题: {q['question']}")
        print(f"期望方向: {q['expected_answer'][:200]}")
        print()


def print_prompt_for_question(q_id: int, strategy: str):
    """打印指定题目和策略的完整 prompt，方便复制到 LLM"""
    strategies = {
        "Direct": DIRECT_PROMPT,
        "RaR": RAR_PROMPT,
        "CoT": COT_PROMPT,
        "RaR+CoT": RAR_COT_PROMPT,
    }

    q = next((q for q in TEST_QUESTIONS if q["id"] == q_id), None)
    if not q:
        print(f"找不到题目 {q_id}")
        return

    if strategy not in strategies:
        print(f"策略 {strategy} 不存在，可选: {list(strategies.keys())}")
        return

    prompt = strategies[strategy].format(question=q["question"])
    print(f"\nQ{q_id} | {q['ambiguity_type']} | {strategy}")
    print(f"原始问题: {q['question']}\n")
    print("--- 完整 Prompt ---")
    print(prompt)
    print("--- 结束 ---")


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 3:
        print_prompt_for_question(int(sys.argv[1]), sys.argv[2])
    else:
        preview_all()
        print("\n用法:")
        print("  python manual_test.py            — 预览所有题目")
        print("  python manual_test.py 1 RaR      — 打印 Q1 的 RaR prompt")
        print("  python manual_test.py 1 RaR+CoT  — 打印 Q1 的 RaR+CoT prompt")

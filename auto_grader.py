"""
自动判分器 — 根据 benchmark 的 ground_truth 判断 LLM 回答是否正确
"""

import re


def grade_answer(response: str, ground_truth: str, acceptable: list, grading: str = "contains") -> dict:
    """
    判断 LLM 回答是否正确

    返回:
        {"correct": bool, "method": str, "detail": str}
    """
    response_lower = response.lower()
    truth_lower = ground_truth.lower()

    if grading == "contains":
        # 检查回答中是否包含标准答案
        if truth_lower in response_lower:
            return {"correct": True, "method": "exact_match", "detail": f"包含 '{ground_truth}'"}
        # 检查可接受的变体
        for alt in acceptable:
            if alt.lower() in response_lower:
                return {"correct": True, "method": "acceptable_match", "detail": f"包含 '{alt}'"}
        return {"correct": False, "method": "not_found", "detail": f"未找到 '{ground_truth}' 或其变体"}

    elif grading == "flexible":
        # 宽松匹配：任一 acceptable 答案出现即可
        for alt in acceptable:
            if alt.lower() in response_lower:
                return {"correct": True, "method": "flexible_match", "detail": f"包含 '{alt}'"}
        return {"correct": False, "method": "flexible_miss", "detail": f"未找到任何可接受答案"}

    return {"correct": False, "method": "unknown_grading", "detail": f"未知判分方式: {grading}"}


def extract_final_answer(response: str) -> str:
    """
    尝试从回答中提取"最终答案"部分，
    优先匹配【最终答案】【答案】【回答】等标签后的内容
    """
    patterns = [
        r'【最终答案】[：:]?\s*(.+?)(?:\n|$)',
        r'\[最终答案\][：:]?\s*(.+?)(?:\n|$)',
        r'【答案】[：:]?\s*(.+?)(?:\n|$)',
        r'\[答案\][：:]?\s*(.+?)(?:\n|$)',
        r'最终答案[：:]\s*(.+?)(?:\n|$)',
        r'【回答】[：:]?\s*(.+?)(?:\n|$)',   # Single-RaR 输出格式
        r'\*\*(?:Answer|Result)[：:]?\*\*\s*(.+?)(?:\n|$)',  # Markdown 加粗答案
        r'(?:Answer|Result)[：:]\s*(.+?)(?:\n|$)',            # 英文 Answer: 标签
    ]
    for pat in patterns:
        m = re.search(pat, response)
        if m:
            return m.group(1).strip()
    # 没有找到标签，返回整体回答（截取最后200字符作为"答案区域"）
    return response[-200:].strip()


def calculate_accuracy(results: list) -> dict:
    """
    从实验结果列表计算各策略准确率

    输入: [{"strategy": "Direct", "grade": {"correct": True/False}, ...}, ...]
    输出: {
        "Direct": {"correct": 8, "total": 12, "accuracy": 66.7},
        ...
    }
    """
    from collections import defaultdict
    stats = defaultdict(lambda: {"correct": 0, "total": 0})

    for r in results:
        s = stats[r["strategy"]]
        s["total"] += 1
        if r["grade"]["correct"]:
            s["correct"] += 1

    output = {}
    for name in ["Direct", "RaR", "CoT", "RaR+CoT"]:
        if name in stats:
            s = stats[name]
            output[name] = {
                "correct": s["correct"],
                "total": s["total"],
                "accuracy": round(s["correct"] / s["total"] * 100, 1),
            }
    return output


def accuracy_by_category(results: list) -> dict:
    """按题目类别分组计算准确率"""
    from collections import defaultdict
    # results 中每条记录包含 category 和 strategy
    stats = defaultdict(lambda: defaultdict(lambda: {"correct": 0, "total": 0}))

    for r in results:
        cat = r.get("category", "UNKNOWN")
        s = stats[cat][r["strategy"]]
        s["total"] += 1
        if r["grade"]["correct"]:
            s["correct"] += 1

    output = {}
    for cat, strategies in stats.items():
        output[cat] = {}
        for strat in ["Direct", "RaR", "CoT", "RaR+CoT"]:
            if strat in strategies:
                s = strategies[strat]
                output[cat][strat] = round(s["correct"] / s["total"] * 100, 1)
    return output

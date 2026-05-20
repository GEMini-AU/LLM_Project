"""
Two-Step RaR 实验 — 论文核心主张：强模型重述问题 → 任意模型回答
  策略对比:
    Direct      — 直接用原始问题回答（基线）
    Single-RaR  — 同一模型先重述再回答（单步 RaR）
    TwoStep-RaR — 重述模型先产出澄清版问题，回答模型用 Direct prompt 回答澄清版
"""

import json
import time
import os
from datetime import datetime
from openai import OpenAI

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from prompts import DIRECT_PROMPT, RAR_PROMPT, REPHRASE_ONLY_PROMPT
from benchmark import BENCHMARK_QUESTIONS
from auto_grader import grade_answer, extract_final_answer, calculate_accuracy, accuracy_by_category

API_KEY = os.environ.get("OPENAI_API_KEY", "")
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL = os.environ.get("MODEL_NAME", "deepseek-chat")

# Two-Step 可指定不同模型，当前用同一模型
REPHRASER_MODEL = os.environ.get("REPHRASER_MODEL", MODEL)
RESPONDER_MODEL = os.environ.get("RESPONDER_MODEL", MODEL)

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def call_llm(prompt: str, model: str = None, max_tokens: int = 1024) -> str:
    try:
        response = client.chat.completions.create(
            model=model or MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[ERROR] {e}"


def run_twostep_experiment():
    """三种策略: Direct / Single-RaR / TwoStep-RaR"""
    strategies = ["Direct", "Single-RaR", "TwoStep-RaR"]
    results = []
    total = len(BENCHMARK_QUESTIONS) * len(strategies)
    current = 0

    for q in BENCHMARK_QUESTIONS:
        og_question = q["question"]

        # === 预先生成 TwoStep 的重述版问题 ===
        rephrase_prompt = REPHRASE_ONLY_PROMPT.format(question=og_question)
        rephrased_q = call_llm(rephrase_prompt, model=REPHRASER_MODEL, max_tokens=512)

        for strategy in strategies:
            current += 1

            if strategy == "Direct":
                prompt = DIRECT_PROMPT.format(question=og_question)
                model_used = MODEL
            elif strategy == "Single-RaR":
                prompt = RAR_PROMPT.format(question=og_question)
                model_used = MODEL
            elif strategy == "TwoStep-RaR":
                # 重述后的问题喂给 Direct prompt
                prompt = DIRECT_PROMPT.format(question=rephrased_q)
                model_used = RESPONDER_MODEL

            print(f"[{current}/{total}] {q['id']} [{q['category']}] — {strategy}")

            start = time.time()
            response = call_llm(prompt, model=model_used)
            elapsed = time.time() - start

            # 判分
            final_answer_area = extract_final_answer(response)
            grade = grade_answer(final_answer_area, q["ground_truth"],
                                 q["acceptable"], q.get("grading", "contains"))
            if not grade["correct"]:
                grade_full = grade_answer(response, q["ground_truth"],
                                          q["acceptable"], q.get("grading", "contains"))
                if grade_full["correct"]:
                    grade = grade_full

            results.append({
                "question_id": q["id"],
                "question": og_question,
                "category": q["category"],
                "ground_truth": q["ground_truth"],
                "ambiguity": q["ambiguity"],
                "strategy": strategy,
                "rephrased_question": rephrased_q if strategy == "TwoStep-RaR" else "",
                "response": response,
                "latency_seconds": round(elapsed, 2),
                "grade": grade,
                "model_used": model_used,
            })

            symbol = "+" if grade["correct"] else "-"
            print(f"  {symbol} {grade['detail']}")

            time.sleep(0.3)

    return results


def save_results(results: list):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"twostep_{MODEL}_{timestamp}.json"

    # 构建类似格式的 metadata
    meta = {
        "model": MODEL,
        "rephraser_model": REPHRASER_MODEL,
        "responder_model": RESPONDER_MODEL,
        "api_base": BASE_URL,
        "timestamp": timestamp,
        "total_questions": len(BENCHMARK_QUESTIONS),
        "strategies": ["Direct", "Single-RaR", "TwoStep-RaR"],
    }

    # 计算准确率
    accuracy_data = {}
    strategy_counts = {"Direct": 0, "Single-RaR": 0, "TwoStep-RaR": 0}
    strategy_correct = {"Direct": 0, "Single-RaR": 0, "TwoStep-RaR": 0}

    cat_accuracy = {}
    cat_counts = {}
    cat_correct = {}
    for strat in ["Direct", "Single-RaR", "TwoStep-RaR"]:
        cat_counts[strat] = {}
        cat_correct[strat] = {}

    for r in results:
        s = r["strategy"]
        strategy_counts[s] += 1
        if r["grade"]["correct"]:
            strategy_correct[s] += 1

        cat = r["category"]
        if cat not in cat_counts[s]:
            cat_counts[s][cat] = 0
            cat_correct[s][cat] = 0
        cat_counts[s][cat] += 1
        if r["grade"]["correct"]:
            cat_correct[s][cat] += 1

    for strat in ["Direct", "Single-RaR", "TwoStep-RaR"]:
        accuracy_data[strat] = {
            "correct": strategy_correct[strat],
            "total": strategy_counts[strat],
            "accuracy": round(strategy_correct[strat] / strategy_counts[strat] * 100, 1)
        }

    # Per-category
    all_cats = sorted(set(r["category"] for r in results))
    for cat in all_cats:
        cat_accuracy[cat] = {}
        for strat in ["Direct", "Single-RaR", "TwoStep-RaR"]:
            total = cat_counts[strat].get(cat, 0)
            correct = cat_correct[strat].get(cat, 0)
            cat_accuracy[cat][strat] = round(correct / total * 100, 1) if total > 0 else 0

    meta["accuracy"] = accuracy_data
    meta["accuracy_by_category"] = cat_accuracy

    output = {"metadata": meta, "results": results}
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print("Two-Step RaR 准确率对比")
    print("-" * 60)
    for strat in ["Direct", "Single-RaR", "TwoStep-RaR"]:
        a = accuracy_data[strat]
        print(f"  {strat:<14}: {a['correct']}/{a['total']} = {a['accuracy']}%")
    print(f"\n结果保存到 {filename}")
    return filename


if __name__ == "__main__":
    if not API_KEY:
        print("[错误] 请先在 .env 文件中设置 OPENAI_API_KEY")
        exit(1)

    print(f"重述模型: {REPHRASER_MODEL}")
    print(f"回答模型: {RESPONDER_MODEL}")
    print(f"题目数: {len(BENCHMARK_QUESTIONS)}, 策略: Direct / Single-RaR / TwoStep-RaR")
    print(f"总调用: {len(BENCHMARK_QUESTIONS) * 3 + len(BENCHMARK_QUESTIONS)} 次\n")
    print("(注: 加号前是 30×3=90 次回答调用, 加号后是 30 次重述调用)\n")

    results = run_twostep_experiment()
    save_results(results)

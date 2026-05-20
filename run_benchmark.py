"""
Benchmark 实验运行器 — 测试 4 种策略在可自动判分题目上的准确率
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

from prompts import DIRECT_PROMPT, RAR_PROMPT, COT_PROMPT, RAR_COT_PROMPT
from benchmark import BENCHMARK_QUESTIONS
from auto_grader import grade_answer, extract_final_answer, calculate_accuracy, accuracy_by_category

API_KEY = os.environ.get("OPENAI_API_KEY", "")
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL = os.environ.get("MODEL_NAME", "gpt-4o-mini")

STRATEGIES = {
    "Direct": DIRECT_PROMPT,
    "RaR": RAR_PROMPT,
    "CoT": COT_PROMPT,
    "RaR+CoT": RAR_COT_PROMPT,
}

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def call_llm(prompt: str, max_tokens: int = 1024) -> str:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[ERROR] {e}"


def run_benchmark():
    results = []
    total = len(BENCHMARK_QUESTIONS) * len(STRATEGIES)
    current = 0

    for q in BENCHMARK_QUESTIONS:
        for strategy_name, strategy_prompt in STRATEGIES.items():
            current += 1
            prompt = strategy_prompt.format(question=q["question"])

            print(f"[{current}/{total}] {q['id']} [{q['category']}] — {strategy_name}")

            start = time.time()
            response = call_llm(prompt)
            elapsed = time.time() - start

            # 自动判分：优先用"最终答案"区域，回退到完整回答
            final_answer_area = extract_final_answer(response)
            grade = grade_answer(
                final_answer_area,
                q["ground_truth"],
                q["acceptable"],
                q.get("grading", "contains"),
            )
            # 如果针对"最后一段"判分失败，用完整回答再试一次
            if not grade["correct"]:
                grade_full = grade_answer(
                    response, q["ground_truth"], q["acceptable"], q.get("grading", "contains")
                )
                if grade_full["correct"]:
                    grade = grade_full

            results.append({
                "question_id": q["id"],
                "question": q["question"],
                "category": q["category"],
                "ground_truth": q["ground_truth"],
                "ambiguity": q["ambiguity"],
                "strategy": strategy_name,
                "response": response,
                "latency_seconds": round(elapsed, 2),
                "grade": grade,
            })

            symbol = "+" if grade["correct"] else "-"
            print(f"  {symbol} {grade['detail']}")

            time.sleep(0.3)

    return results


def save_results(results: list):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"benchmark_{MODEL}_{timestamp}.json"

    accuracy = calculate_accuracy(results)
    category_acc = accuracy_by_category(results)

    output = {
        "metadata": {
            "model": MODEL,
            "api_base": BASE_URL,
            "timestamp": timestamp,
            "total_questions": len(BENCHMARK_QUESTIONS),
            "strategies": list(STRATEGIES.keys()),
            "accuracy": accuracy,
            "accuracy_by_category": category_acc,
        },
        "results": results,
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print("准确率总览")
    print("-" * 60)
    for strat in ["Direct", "RaR", "CoT", "RaR+CoT"]:
        if strat in accuracy:
            a = accuracy[strat]
            print(f"  {strat:<12}: {a['correct']}/{a['total']} = {a['accuracy']}%")

    print(f"\n结果已保存到 {filename}")
    return filename


if __name__ == "__main__":
    if not API_KEY or API_KEY == "your-api-key-here":
        print("[错误] 请先在 .env 文件中设置 OPENAI_API_KEY")
        exit(1)

    print(f"模型: {MODEL}")
    print(f"Benchmark 题目数: {len(BENCHMARK_QUESTIONS)}")
    print(f"策略数: {len(STRATEGIES)}, 总调用: {len(BENCHMARK_QUESTIONS) * len(STRATEGIES)}\n")

    results = run_benchmark()
    save_results(results)
    print("\nBenchmark 完成。运行 python visualize.py 生成图表。")

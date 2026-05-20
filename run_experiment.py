"""
实验运行器 — 测试四种 Prompt 策略在同一模型上的表现
"""

import json
import time
import os
from datetime import datetime
from openai import OpenAI

# 自动加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from prompts import DIRECT_PROMPT, RAR_PROMPT, COT_PROMPT, RAR_COT_PROMPT
from test_set import TEST_QUESTIONS

# ============================================================
# 配置 — 通过 .env 文件 或 环境变量设置
# ============================================================
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
    """调用 LLM，返回文本响应"""
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


def run_single_experiment():
    """逐个问题 × 四种策略 测试"""
    results = []
    total = len(TEST_QUESTIONS) * len(STRATEGIES)
    current = 0

    for q in TEST_QUESTIONS:
        for strategy_name, strategy_prompt in STRATEGIES.items():
            current += 1
            prompt = strategy_prompt.format(question=q["question"])

            print(f"[{current}/{total}] Q{q['id']} [{q['ambiguity_type']}] — {strategy_name}")

            start = time.time()
            answer = call_llm(prompt)
            elapsed = time.time() - start

            results.append(
                {
                    "question_id": q["id"],
                    "question": q["question"],
                    "ambiguity_type": q["ambiguity_type"],
                    "ambiguity_desc": q["ambiguity_desc"],
                    "expected": q["expected_answer"],
                    "strategy": strategy_name,
                    "prompt_used": prompt,
                    "response": answer,
                    "latency_seconds": round(elapsed, 2),
                }
            )

            # 策略间短暂延迟，避免 API 限流
            time.sleep(0.5)

    return results


def save_results(results: list):
    """保存结果到 JSON 文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"results_{MODEL}_{timestamp}.json"
    output = {
        "metadata": {
            "model": MODEL,
            "api_base": BASE_URL,
            "timestamp": timestamp,
            "total_questions": len(TEST_QUESTIONS),
            "strategies": list(STRATEGIES.keys()),
        },
        "results": results,
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到 {filename}")
    return filename


if __name__ == "__main__":
    if not API_KEY or API_KEY == "your-api-key-here":
        print("[错误] 请先在 .env 文件中设置 OPENAI_API_KEY")
        print("如果没有 .env 文件，请复制 .env.example 为 .env 并填入你的 API Key")
        exit(1)

    print(f"模型: {MODEL}")
    print(f"API: {BASE_URL}")
    print(f"题目数: {len(TEST_QUESTIONS)}, 策略数: {len(STRATEGIES)}")
    print(f"预计 API 调用次数: {len(TEST_QUESTIONS) * len(STRATEGIES)}\n")

    results = run_single_experiment()
    save_results(results)
    print("实验完成。")

"""dataset_combined.json — 随机抽20题, Direct vs RaR"""
import json, time, random, re, os, sys
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
from prompts import DIRECT_PROMPT, RAR_PROMPT, DIRECT_PROMPT_EN, RAR_PROMPT_EN
from auto_grader import grade_answer
from collections import defaultdict, Counter

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url=os.environ["OPENAI_BASE_URL"])
MODEL = os.environ.get("MODEL_NAME", "deepseek-chat")
random.seed(42)

# 加载
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset_combined.json"), encoding="utf-8") as f:
    data = json.load(f)

n = int(sys.argv[1]) if len(sys.argv) >= 2 else len(data)
sample = random.sample(data, min(n, len(data)))
types = Counter(q["task_name"] for q in sample)
print(f"题库 {len(data)} 题, 抽 {len(sample)} 题")
for t, n in sorted(types.items()):
    print(f"  {t}: {n}")
print(f"总调用: {len(sample)*2} 次\n")

# 判断中文: xingce_ 开头
cn_strategies = {"Direct": DIRECT_PROMPT, "RaR": RAR_PROMPT}
en_strategies = {"Direct": DIRECT_PROMPT_EN, "RaR": RAR_PROMPT_EN}

results = []
current = 0
for q in sample:
    is_cn = q["task_name"].startswith("xingce")
    strategies = cn_strategies if is_cn else en_strategies
    for sname, sprompt in strategies.items():
        current += 1
        prompt = sprompt.format(question=q["question"])
        print(f"[{current}/{len(sample)*2}] {q['task_name']} — {sname}")

        r = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0.0, max_tokens=1024)
        resp = r.choices[0].message.content.strip()

        # 判分
        ans = q["answer"]
        acceptable = [ans, ans.lower(), ans.upper()]
        if ans.lower() in ("yes", "no"):
            acceptable += ["Yes", "yes", "YES", "No", "no", "NO"]
        # 行测ABCD
        if re.match(r'^[A-D]$', ans):
            acceptable += [ans, ans.lower(), ans.upper()]

        grade = grade_answer(resp, ans, acceptable, "contains")

        results.append({
            "question_id": f"{q['task_name']}_{current}",
            "question": q["question"][:200],
            "category": q["task_name"],
            "ground_truth": ans,
            "strategy": sname,
            "response": resp,
            "grade": grade,
        })
        ok = "+" if grade["correct"] else "-"
        print(f"  {ok} {grade['detail']}")
        time.sleep(0.2)

# 统计
acc = defaultdict(lambda: {"c": 0, "t": 0})
cat_acc = defaultdict(lambda: defaultdict(lambda: {"c": 0, "t": 0}))
for r in results:
    acc[r["strategy"]]["t"] += 1
    acc[r["strategy"]]["c"] += r["grade"]["correct"]
    cat_acc[r["category"]][r["strategy"]]["t"] += 1
    cat_acc[r["category"]][r["strategy"]]["c"] += r["grade"]["correct"]

print(f"\n{'='*60}")
print("准确率总览")
for s in ["Direct", "RaR"]:
    a = acc[s]
    print(f"  {s}: {a['c']}/{a['t']} = {round(a['c']/a['t']*100, 1)}%")

print(f"\n按类型:")
for cat in sorted(cat_acc.keys()):
    d = cat_acc[cat]["Direct"]; r = cat_acc[cat]["RaR"]
    da = round(d["c"]/d["t"]*100, 1) if d["t"] > 0 else 0
    ra = round(r["c"]/r["t"]*100, 1) if r["t"] > 0 else 0
    print(f"  {cat}: Direct={da}% | RaR={ra}%")

# 保存
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
fname = f"combined_{MODEL}_n20_{ts}.json"
out = {
    "metadata": {
        "model": MODEL, "timestamp": ts, "total": len(sample),
        "strategies": ["Direct", "RaR"],
        "accuracy": {
            s: {"correct": acc[s]["c"], "total": acc[s]["t"],
                "accuracy": round(acc[s]["c"]/acc[s]["t"]*100, 1)}
            for s in ["Direct", "RaR"]
        },
        "accuracy_by_category": {
            cat: {
                s: round(cat_acc[cat][s]["c"]/cat_acc[cat][s]["t"]*100, 1)
                for s in ["Direct", "RaR"]
            }
            for cat in cat_acc
        },
    },
    "results": results,
}
with open(fname, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"\n结果: {fname}")

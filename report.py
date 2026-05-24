"""
HTML 报告生成器 — 中英双语，支持 benchmark 和定性分析
用法: python report.py <xxx.json>
"""

import json
import sys
import os
import base64
from datetime import datetime


def load_results(filename: str) -> dict:
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def img_to_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


CATEGORY_CN = {
    "coin_flip": "硬币翻转 Coin Flip",
    "even_day": "偶数日 Even Day",
    "even_month": "偶数月 Even Month",
    "last_letter": "尾字母拼接 Last Letter",
    "SIMPLE": "简单题 SIMPLE",
    "AMBIG": "歧义题 AMBIG",
    "COMPLEX": "复杂题 COMPLEX",
    "MIXED": "混合题 MIXED",
    "HARD": "困难题 HARD",
}

TASK_DESC_CN = {
    "coin_flip": "追踪硬币初始状态，依次判断每人是否翻转，最终确定硬币正反面。Track coin state through flips.",
    "even_day": "判断名人的出生日期是否为偶数日。Check if celebrity was born on an even day.",
    "even_month": "判断名人的出生月份是否为偶数月。Check if celebrity was born in an even month.",
    "last_letter": "取每个单词的最后一个字母，按顺序拼接成字符串。Concatenate last letters of words.",
}

ANSWER_CN = {"Yes": "是 Yes", "No": "否 No", "yes": "是 Yes", "no": "否 No"}


def build_question_table(results: list) -> str:
    from collections import OrderedDict
    has_grading = "grade" in results[0] if results else False
    is_benchmark = "ground_truth" in results[0] if results else False

    by_q = OrderedDict()
    for r in results:
        qid = r["question_id"]
        if qid not in by_q:
            entry = {"question": r["question"], "strategies": {}}
            if is_benchmark:
                entry["category"] = r.get("category", "")
                entry["ground_truth"] = r.get("ground_truth", "")
                entry["ambiguity"] = r.get("ambiguity", "")
            else:
                entry["ambiguity_type"] = r.get("ambiguity_type", "")
                entry["ambiguity_desc"] = r.get("ambiguity_desc", "")
                entry["expected"] = r.get("expected", "")
            by_q[qid] = entry
        by_q[qid]["strategies"][r["strategy"]] = r

    all_strategies = sorted(set(r["strategy"] for r in results))

    rows = ""
    for qid, qdata in by_q.items():
        strat_html = ""
        for sname in all_strategies:
            r = qdata["strategies"].get(sname)
            if not r:
                continue
            latency = r.get("latency_seconds", 0)
            response = r["response"].replace("<", "&lt;").replace(">", "&gt;")
            response_cn = r.get("response_cn", "").replace("<", "&lt;").replace(">", "&gt;") if "response_cn" in r else ""

            if has_grading:
                correct = r["grade"]["correct"]
                badge = '<span class="badge-ok">OK / 正确</span>' if correct else '<span class="badge-fail">FAIL / 错误</span>'
                col_class = "correct" if correct else "incorrect"
            else:
                badge = ""
                col_class = "qualitative"

            cn_block = '<div class="strat-response-cn">{}</div>'.format(response_cn) if response_cn else ""
            strat_html += '<div class="strat-col {}"><div class="strat-header"><b>{}</b> {} <span class="latency">{:.1f}s</span></div><div class="strat-response">{}</div>{}</div>'.format(
                col_class, sname, badge, latency, response, cn_block
            )

        if is_benchmark:
            cat_label = CATEGORY_CN.get(qdata["category"], qdata["category"])
            truth = qdata["ground_truth"]
            truth_bilingual = ANSWER_CN.get(truth, truth)
            task_desc = TASK_DESC_CN.get(qdata.get("category", ""), "")
            header_extra = '<span class="q-category">[{}]</span><span class="q-truth">答案 Answer: {}</span>'.format(
                cat_label, truth_bilingual
            )
            amb_html = '<div class="q-task-desc">{}</div>'.format(task_desc) if task_desc else ""
        else:
            header_extra = '<span class="q-category">[{}]</span>'.format(qdata["ambiguity_type"])
            amb_html = '<div class="q-ambiguity">歧义 Ambiguity: {}</div><div class="q-expected">预期 Expected: {}</div>'.format(
                qdata["ambiguity_desc"][:150], qdata["expected"][:200]
            )

        rows += '<div class="question-block"><div class="q-header"><span class="q-id">{}</span>{}<span class="q-text">{}</span></div>{}<div class="strat-grid">{}</div></div>'.format(
            qid, header_extra, qdata["question"], amb_html, strat_html
        )
    return rows


def _get_strategy_names(meta: dict) -> list:
    strategies = meta.get("strategies", [])
    if strategies:
        return strategies
    acc = meta.get("accuracy", {})
    if acc:
        return list(acc.keys())
    return ["Direct", "RaR"]


def build_accuracy_table(meta: dict) -> str:
    acc = meta.get("accuracy", {})
    rows = ""
    for sname in _get_strategy_names(meta):
        if sname in acc:
            a = acc[sname]
            rows += "<tr><td>{}</td><td>{}/{}</td><td class='acc-val'>{}%</td></tr>".format(
                sname, a["correct"], a["total"], a["accuracy"]
            )
    return rows


def build_category_table(meta: dict) -> str:
    cat_acc = meta.get("accuracy_by_category", {})
    strategies = _get_strategy_names(meta)
    lines = ""
    for cat, strats in cat_acc.items():
        cat_label = CATEGORY_CN.get(cat, cat)
        cells = "<td class='cat-name'>{}</td>".format(cat_label)
        for sname in strategies:
            val = strats.get(sname, "-")
            if val == 100.0:
                cls = "acc-perfect"
            elif isinstance(val, (int, float)) and val >= 80:
                cls = "acc-good"
            else:
                cls = "acc-mid"
            cells += "<td class='{}'>{}%</td>".format(cls, val)
        lines += "<tr>{}</tr>".format(cells)
    return lines


CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:"Microsoft YaHei","SimHei",sans-serif; background:#f5f6fa; color:#2c3e50; line-height:1.6; }
.container { max-width:1400px; margin:0 auto; padding:24px; }
.cover { background:linear-gradient(135deg,#2c3e50,#34495e); color:white; padding:48px; border-radius:12px; margin-bottom:32px; text-align:center; }
.cover h1 { font-size:32px; margin-bottom:8px; }
.cover .subtitle { font-size:16px; opacity:0.8; }
.cover .meta { margin-top:16px; font-size:13px; opacity:0.6; }
.summary { display:flex; gap:16px; margin-bottom:32px; flex-wrap:wrap; }
.card { background:white; border-radius:10px; padding:20px 24px; box-shadow:0 2px 8px rgba(0,0,0,0.06); flex:1; min-width:200px; }
.card h3 { font-size:13px; color:#7f8c8d; margin-bottom:8px; letter-spacing:0.5px; }
.card .big-num { font-size:36px; font-weight:bold; }
.section-title { font-size:20px; margin:32px 0 16px; padding-bottom:8px; border-bottom:2px solid #3498db; }
table { width:100%; border-collapse:collapse; background:white; border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.06); }
th,td { padding:12px 16px; text-align:center; font-size:14px; }
th { background:#34495e; color:white; font-weight:500; }
tr:nth-child(even) { background:#f9fafb; }
.acc-val { font-weight:bold; font-size:18px; color:#2ecc71; }
.cat-name { font-weight:bold; text-align:left; }
.acc-perfect { color:#2ecc71; font-weight:bold; }
.acc-good { color:#27ae60; }
.acc-mid { color:#e67e22; }
.question-block { background:white; border-radius:10px; padding:20px; margin-bottom:20px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }
.q-header { display:flex; align-items:center; gap:12px; margin-bottom:6px; flex-wrap:wrap; }
.q-id { background:#3498db; color:white; padding:2px 10px; border-radius:4px; font-weight:bold; font-size:13px; }
.q-category { color:#95a5a6; font-size:12px; }
.q-text { font-size:16px; font-weight:bold; }
.q-truth { color:#e74c3c; font-size:13px; border:1px solid #e74c3c; padding:2px 8px; border-radius:4px; }
.q-task-desc { font-size:12px; color:#7f8c8d; margin-bottom:8px; background:#f0f4ff; padding:6px 10px; border-radius:4px; border-left:3px solid #3498db; }
.q-ambiguity { font-size:12px; color:#95a5a6; margin-bottom:4px; font-style:italic; }
.q-expected { font-size:12px; color:#2c3e50; margin-bottom:8px; background:#eefaf5; padding:6px 10px; border-radius:4px; border-left:3px solid #2ecc71; }
.strat-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-top:12px; }
@media(max-width:1200px){ .strat-grid{grid-template-columns:repeat(2,1fr);} }
.strat-col { border-radius:8px; padding:12px; border:1px solid #ecf0f1; }
.strat-col.correct { border-left:4px solid #2ecc71; }
.strat-col.incorrect { border-left:4px solid #e74c3c; background:#fdf2f2; }
.strat-col.qualitative { border-left:4px solid #3498db; }
.strat-header { font-size:13px; font-weight:bold; margin-bottom:8px; display:flex; align-items:center; gap:8px; }
.strat-response { font-size:12px; max-height:220px; overflow-y:auto; white-space:pre-wrap; color:#555; }
.strat-response-cn { font-size:12px; max-height:220px; overflow-y:auto; white-space:pre-wrap; color:#2c3e50; background:#fffdf0; padding:8px 10px; margin-top:8px; border-radius:4px; border-left:3px solid #f39c12; }
.latency { font-size:11px; color:#95a5a6; font-weight:normal; }
.badge-ok { background:#2ecc71; color:white; padding:1px 8px; border-radius:3px; font-size:11px; }
.badge-fail { background:#e74c3c; color:white; padding:1px 8px; border-radius:3px; font-size:11px; }
.charts-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:20px; margin-top:16px; }
@media(max-width:1000px){ .charts-grid{grid-template-columns:1fr;} }
.chart-card { background:white; border-radius:10px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.06); text-align:center; }
.chart-card img { width:100%; display:block; }
.chart-caption { padding:10px; font-size:13px; color:#7f8c8d; }
"""


def generate_report(json_path: str):
    data = load_results(json_path)
    meta = data["metadata"]
    results = data["results"]

    has_grading = "grade" in results[0] if results else False
    has_category = "category" in results[0] if results else False

    chart_dir = json_path.replace(".json", "_charts")
    charts = {}
    if os.path.isdir(chart_dir):
        for f in sorted(os.listdir(chart_dir)):
            if f.endswith(".png"):
                charts[f.replace(".png", "")] = img_to_b64(os.path.join(chart_dir, f))

    question_rows = build_question_table(results)

    # 准确率区域
    acc_section = ""
    if has_grading:
        acc_rows = build_accuracy_table(meta)
        cat_rows = build_category_table(meta)
        cat_table_html = ""
        if has_category:
            strats = _get_strategy_names(meta)
            cat_header = "<tr><th>类别 Category</th>" + "".join("<th>{}</th>".format(s) for s in strats) + "</tr>"
            cat_table_html = '<h2 class="section-title">2. 按类别准确率 Accuracy by Category</h2><table>{}{}</table>'.format(
                cat_header, cat_rows
            )
        acc_section = """<h2 class="section-title">1. 整体准确率 Overall Accuracy</h2>
        <table><tr><th>策略 Strategy</th><th>正确/总数 Correct/Total</th><th>准确率 Accuracy</th></tr>{}</table>{}""".format(
            acc_rows, cat_table_html
        )

    # 图表区域
    chart_section = ""
    if charts:
        chart_num = "3" if has_grading else "1"
        chart_imgs = ""
        for name, b64 in charts.items():
            chart_imgs += '<div class="chart-card"><img src="data:image/png;base64,{}" alt="{}"/><div class="chart-caption">{}</div></div>'.format(
                b64, name, name
            )
        chart_section = '<h2 class="section-title">{}. 可视化图表 Charts</h2><div class="charts-grid">{}</div>'.format(
            chart_num, chart_imgs
        )

    # 概览卡片
    has_acc_data = "accuracy" in meta
    if has_acc_data:
        direct_acc = meta.get("accuracy", {}).get("Direct", {}).get("accuracy", "-")
        rar_acc = meta.get("accuracy", {}).get("RaR", {}).get("accuracy", "-")
        summary_cards = """<div class="card"><h3>Direct 准确率 Accuracy</h3><div class="big-num" style="color:#e74c3c;">{}%</div></div>
        <div class="card"><h3>RaR 准确率 Accuracy</h3><div class="big-num" style="color:#2ecc71;">{}%</div></div>""".format(
            direct_acc, rar_acc
        )
    else:
        summary_cards = '<div class="card"><h3>实验类型 Type</h3><div class="big-num" style="font-size:18px;">定性 Qualitative</div></div>'

    report_type = "Benchmark / 基准准确率" if has_grading else "Qualitative / 定性对比"
    question_num = "4" if has_grading else "2"

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RaR 实验报告 Experiment Report — {model}</title>
<style>{css}</style>
</head>
<body>
<div class="container">
<div class="cover">
    <h1>RaR 实验报告 Experiment Report</h1>
    <div class="subtitle">Rephrase and Respond — Prompt 策略对比 {rtype}</div>
    <div class="meta">模型 Model: {model} | API: {api} | 生成时间 Gen: {ts} | 题目 Questions: {nq} | 策略 Strategies: {ns}</div>
</div>
<div class="summary">
    <div class="card"><h3>总题数 Questions</h3><div class="big-num">{nq}</div></div>
    <div class="card"><h3>策略数 Strategies</h3><div class="big-num">{ns}</div></div>
    <div class="card"><h3>模型 Model</h3><div class="big-num" style="font-size:22px;">{model}</div></div>
    {cards}
</div>
{acc}
{charts}
<h2 class="section-title">{qn}. 逐题对比 Per-Question Comparison</h2>
{questions}
</div>
</body>
</html>""".format(
        model=meta.get("model", "unknown"),
        css=CSS,
        rtype=report_type,
        api=meta.get("api_base", "N/A"),
        ts=datetime.now().strftime("%Y-%m-%d %H:%M"),
        nq=meta.get("total_questions", meta.get("total", 0)),
        ns=len(meta.get("strategies", [])),
        cards=summary_cards,
        acc=acc_section,
        charts=chart_section,
        qn=question_num,
        questions=question_rows,
    )

    report_path = json_path.replace(".json", "_report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("Report saved: {}".format(report_path))
    return report_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        import glob
        files = sorted(glob.glob("*.json"))
    else:
        files = [sys.argv[1]]

    for f in files:
        if not os.path.exists(f):
            print("File not found: {}".format(f))
            continue
        # 跳过数据集文件（非结果文件）
        if f.startswith("dataset_"):
            print("Skipping dataset: {}".format(f))
            continue
        print("Processing {} ...".format(f))
        generate_report(f)

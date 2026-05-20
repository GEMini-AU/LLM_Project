"""
可视化脚本 — 从实验结果 JSON 生成 PPT 可直接用的图表
"""

import json
import sys
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.font_manager as fm
import numpy as np
from collections import defaultdict

# ============================================================
# 全局样式 — 学术风格，强制使用 SimHei 中文字体
# ============================================================
SIMHEI_PATH = "C:\\Windows\\Fonts\\simhei.ttf"
fm.fontManager.addfont(SIMHEI_PATH)
CHINESE_FONT = fm.FontProperties(fname=SIMHEI_PATH)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["SimHei"],
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "axes.grid": True,
    "grid.alpha": 0.3,
})
# 强制重建字体缓存
fm._load_fontmanager(try_read_cache=False)

DEFAULT_COLORS = ["#E74C3C", "#2ECC71", "#3498DB", "#9B59B6", "#F39C12", "#1ABC9C", "#E67E22", "#8E44AD"]
STRATEGY_COLORS = {}  # 动态填充
STRATEGY_ORDER = []   # 动态填充

def _init_strategy_info(results: list):
    """从数据中提取所有策略名并分配颜色"""
    global STRATEGY_ORDER, STRATEGY_COLORS
    seen = []
    for r in results:
        s = r["strategy"]
        if s not in seen:
            seen.append(s)
    STRATEGY_ORDER = seen
    STRATEGY_COLORS = {}
    for i, s in enumerate(seen):
        STRATEGY_COLORS[s] = DEFAULT_COLORS[i % len(DEFAULT_COLORS)]


def load_results(filename: str) -> dict:
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 图1: 整体准确率对比柱状图
# ============================================================
def plot_overall_accuracy(data: dict, outdir: str):
    acc = data["metadata"].get("accuracy", {})
    names = [s for s in STRATEGY_ORDER if s in acc]
    values = [acc[s]["accuracy"] for s in names]
    colors = [STRATEGY_COLORS[s] for s in names]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(names, values, color=colors, edgecolor="white", linewidth=0.8, width=0.55)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                f"{val}%", ha="center", va="bottom", fontsize=13, fontweight="bold")

    ax.set_ylabel("Accuracy (%)", fontsize=12)
    ax.set_title(f"Overall Accuracy by Prompt Strategy\nModel: {data['metadata']['model']}",
                 fontsize=14, fontweight="bold")
    ax.set_ylim(0, max(values) + 15)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "01_overall_accuracy.png"))
    plt.close(fig)
    print(f"  -> {outdir}/01_overall_accuracy.png")


# ============================================================
# 图2: 按题目类别分组的准确率
# ============================================================
def plot_category_accuracy(data: dict, outdir: str):
    cat_acc = data["metadata"].get("accuracy_by_category", {})
    if not cat_acc:
        print("  (无 category 数据，跳过图2)")
        return

    categories = list(cat_acc.keys())
    x = np.arange(len(categories))
    width = 0.2
    n_strategies = len(STRATEGY_ORDER)

    fig, ax = plt.subplots(figsize=(10, 5))
    for i, strat in enumerate(STRATEGY_ORDER):
        vals = [cat_acc[cat].get(strat, 0) for cat in categories]
        offset = (i - n_strategies / 2 + 0.5) * width
        bars = ax.bar(x + offset, vals, width, label=strat,
                      color=STRATEGY_COLORS[strat], edgecolor="white", linewidth=0.5)
        for bar, val in zip(bars, vals):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.8,
                        f"{val}%", ha="center", va="bottom", fontsize=7, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=10)
    ax.set_ylabel("Accuracy (%)", fontsize=12)
    ax.set_title("Accuracy by Question Category", fontsize=14, fontweight="bold")
    ax.legend(loc="lower right", fontsize=9)
    ax.set_ylim(0, 115)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "02_category_accuracy.png"))
    plt.close(fig)
    print(f"  -> {outdir}/02_category_accuracy.png")


# ============================================================
# 图3: 延迟对比箱线图
# ============================================================
def plot_latency(data: dict, outdir: str):
    results = data["results"]
    lat_by_strat = defaultdict(list)
    for r in results:
        lat_by_strat[r["strategy"]].append(r["latency_seconds"])

    fig, ax = plt.subplots(figsize=(8, 5))
    strat_names = [s for s in STRATEGY_ORDER if s in lat_by_strat]
    data_groups = [lat_by_strat[s] for s in strat_names]
    colors = [STRATEGY_COLORS[s] for s in strat_names]

    bp = ax.boxplot(data_groups, labels=strat_names, patch_artist=True,
                    widths=0.45, showfliers=True, showmeans=True,
                    meanprops=dict(marker="D", markerfacecolor="black", markersize=5))

    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax.set_ylabel("Latency (seconds)", fontsize=12)
    ax.set_title("Response Latency Comparison", fontsize=14, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "03_latency.png"))
    plt.close(fig)
    print(f"  -> {outdir}/03_latency.png")


# ============================================================
# 图4: 响应长度对比
# ============================================================
def plot_response_length(data: dict, outdir: str):
    results = data["results"]
    len_by_strat = defaultdict(list)
    for r in results:
        len_by_strat[r["strategy"]].append(len(r["response"]))

    strat_names = [s for s in STRATEGY_ORDER if s in len_by_strat]
    means = [np.mean(len_by_strat[s]) for s in strat_names]
    stds = [np.std(len_by_strat[s]) for s in strat_names]
    colors = [STRATEGY_COLORS[s] for s in strat_names]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(strat_names, means, color=colors, edgecolor="white", linewidth=0.8,
                  width=0.55, yerr=stds, capsize=5, error_kw={"linewidth": 1})

    for bar, mean_val in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(stds) * 0.3,
                f"{mean_val:.0f}", ha="center", va="bottom", fontsize=11, fontweight="bold")

    ax.set_ylabel("Avg Response Length (chars)", fontsize=12)
    ax.set_title("Average Response Length by Strategy", fontsize=14, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "04_response_length.png"))
    plt.close(fig)
    print(f"  -> {outdir}/04_response_length.png")


# ============================================================
# 图5: 逐题正确率矩阵（热力图）
# ============================================================
def plot_question_heatmap(data: dict, outdir: str):
    results = data["results"]
    # 按问题分组
    q_ids = sorted(set(r["question_id"] for r in results))
    strat_names = [s for s in STRATEGY_ORDER if s in set(r["strategy"] for r in results)]

    matrix = np.zeros((len(strat_names), len(q_ids)))
    for r in results:
        row = strat_names.index(r["strategy"])
        col = q_ids.index(r["question_id"])
        matrix[row, col] = 1 if r["grade"]["correct"] else 0

    fig, ax = plt.subplots(figsize=(max(8, len(q_ids) * 1.2), 4))
    cmap = matplotlib.colors.ListedColormap(["#E74C3C", "#2ECC71"])
    im = ax.imshow(matrix, cmap=cmap, aspect="auto", vmin=0, vmax=1)

    ax.set_xticks(range(len(q_ids)))
    ax.set_xticklabels(q_ids, fontsize=9)
    ax.set_yticks(range(len(strat_names)))
    ax.set_yticklabels(strat_names, fontsize=11)

    for i in range(len(strat_names)):
        for j in range(len(q_ids)):
            symbol = "+" if matrix[i, j] == 1 else "-"
            color = "white" if matrix[i, j] == 1 else "white"
            ax.text(j, i, symbol, ha="center", va="center", fontsize=14, fontweight="bold",
                    color=color)

    ax.set_title("Per-Question Correctness Heatmap\n(+ = Correct, - = Incorrect)",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "05_question_heatmap.png"))
    plt.close(fig)
    print(f"  -> {outdir}/05_question_heatmap.png")


# ============================================================
# 图6: 与原实验结果结合 — 歧义识别能力雷达图
# ============================================================
def plot_radar(data: dict, outdir: str):
    """综合评估雷达图：准确率 + 响应完整度"""
    # 从结果中计算各维度得分
    results = data["results"]
    acc = data["metadata"].get("accuracy", {})

    categories_acc = data["metadata"].get("accuracy_by_category", {})
    cat_names = list(categories_acc.keys()) if categories_acc else ["MATH", "LOGIC", "FACT", "CODE"]

    # 雷达图：每个策略在各维度上的得分
    angles = np.linspace(0, 2 * np.pi, len(cat_names), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))

    for strat in STRATEGY_ORDER:
        if strat not in acc:
            continue
        values = [categories_acc.get(cat, {}).get(strat, 0) for cat in cat_names]
        values += values[:1]
        ax.fill(angles, values, alpha=0.15, color=STRATEGY_COLORS[strat])
        ax.plot(angles, values, "o-", linewidth=2, color=STRATEGY_COLORS[strat], label=strat)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(cat_names, fontsize=11)
    ax.set_ylim(0, 110)
    ax.set_title("Accuracy Radar by Strategy & Category", fontsize=14, fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=10)

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "06_radar.png"))
    plt.close(fig)
    print(f"  -> {outdir}/06_radar.png")


# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python visualize.py <benchmark_results.json>")
        print("      python visualize.py all  (处理所有 benchmark_*.json)")
        sys.exit(1)

    if sys.argv[1] == "all":
        # 找当前目录下所有 benchmark 结果
        files = sorted([f for f in os.listdir(".") if f.startswith("benchmark_") and f.endswith(".json")])
        if not files:
            print("未找到 benchmark_*.json，运行 python run_benchmark.py 先。")
            sys.exit(1)
    else:
        files = [sys.argv[1]]

    for f in files:
        print(f"\n处理 {f} ...")
        data = load_results(f)

        # 从数据中动态检测策略名（兼容不同实验）
        _init_strategy_info(data["results"])

        # 为每个结果文件创建图表子目录
        chart_dir = f.replace(".json", "_charts")
        os.makedirs(chart_dir, exist_ok=True)

        plot_overall_accuracy(data, chart_dir)
        plot_category_accuracy(data, chart_dir)
        plot_latency(data, chart_dir)
        plot_response_length(data, chart_dir)
        plot_question_heatmap(data, chart_dir)
        plot_radar(data, chart_dir)

        print(f"图表已生成到 {chart_dir}/")

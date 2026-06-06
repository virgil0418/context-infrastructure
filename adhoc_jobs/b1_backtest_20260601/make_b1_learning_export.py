from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


SRC_DIR = Path(r"F:\z哥\runs\20260601-b1-year-backtest-final")
OUT_DIR = Path(r"F:\z哥\runs\20260601-b1-learning-samples")


LEARNING_FIELDS = [
    "month",
    "code",
    "name",
    "industry",
    "signal_date",
    "entry_date",
    "exit_date",
    "b1_close",
    "entry_price",
    "stop_price",
    "initial_risk_pct",
    "final_exit_price",
    "total_return_pct",
    "max_return_pct",
    "adverse_return_pct",
    "r_multiple",
    "days_held",
    "exit_reason",
    "partial_actions",
    "j_value",
    "pct_chg_signal",
    "amplitude_signal",
    "wl",
    "yl",
    "formula_satisfied",
    "formula_missing",
    "z_satisfied",
    "z_missing",
    "historical_like",
    "risk_flags",
    "setup_score",
    "setup_grade",
    "learning_bucket",
    "operation",
]


def bucket(row: dict) -> str:
    ret = float(row["total_return_pct"])
    if "止损" in row["exit_reason"]:
        return "反例-止损"
    if row["exit_reason"] == "3天未恢复上涨":
        return "反例-没涨就走"
    if "盈转亏" in row["exit_reason"]:
        return "边界-盈转亏"
    if ret >= 10:
        return "正例-强收益"
    if ret > 0:
        return "正例-小赚或防守成功"
    return "边界-不亏或小亏"


def summarize(rows: list[dict]) -> dict:
    if not rows:
        return {}
    returns = [float(row["total_return_pct"]) for row in rows]
    wins = [value for value in returns if value > 0]
    return {
        "count": len(rows),
        "win_count": len(wins),
        "win_rate_pct": round(len(wins) / len(rows) * 100, 2),
        "avg_return_pct": round(sum(returns) / len(returns), 2),
        "median_return_pct": round(sorted(returns)[len(returns) // 2], 2),
        "best_return_pct": round(max(returns), 2),
        "worst_return_pct": round(min(returns), 2),
        "exit_reasons": dict(Counter(row["exit_reason"] for row in rows).most_common()),
        "learning_buckets": dict(Counter(row["learning_bucket"] for row in rows).most_common()),
    }


def write_csv(path: Path, rows: list[dict], fields: list[str] = LEARNING_FIELDS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads((SRC_DIR / "trade_backtest.json").read_text(encoding="utf-8"))
    rows: list[dict] = []
    for row in data["trades"]:
        item = dict(row)
        item["month"] = item["signal_date"][:7]
        item["learning_bucket"] = bucket(item)
        rows.append(item)

    write_csv(OUT_DIR / "all_b1_learning_samples.csv", rows)
    (OUT_DIR / "all_b1_learning_samples.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    by_month: dict[str, list[dict]] = defaultdict(list)
    by_bucket: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_month[row["month"]].append(row)
        by_bucket[row["learning_bucket"]].append(row)

    for month, items in sorted(by_month.items()):
        write_csv(OUT_DIR / "by_month" / f"{month}.csv", items)
    for name, items in sorted(by_bucket.items()):
        safe_name = name.replace("/", "_")
        write_csv(OUT_DIR / "by_bucket" / f"{safe_name}.csv", items)

    strong_examples = sorted(
        [row for row in rows if row["learning_bucket"] == "正例-强收益"],
        key=lambda row: (-float(row["total_return_pct"]), -float(row["max_return_pct"])),
    )[:100]
    stop_examples = sorted(
        [row for row in rows if row["learning_bucket"] == "反例-止损"],
        key=lambda row: (float(row["total_return_pct"]), float(row["adverse_return_pct"])),
    )[:100]
    no_rise_examples = sorted(
        [row for row in rows if row["learning_bucket"] == "反例-没涨就走"],
        key=lambda row: (float(row["total_return_pct"]), -float(row["setup_score"])),
    )[:100]
    boundary_examples = sorted(
        [row for row in rows if row["learning_bucket"].startswith("边界")],
        key=lambda row: (abs(float(row["total_return_pct"])), -float(row["max_return_pct"])),
    )[:100]

    write_csv(OUT_DIR / "study_index_positive_top100.csv", strong_examples)
    write_csv(OUT_DIR / "study_index_stoploss_top100.csv", stop_examples)
    write_csv(OUT_DIR / "study_index_no_rise_top100.csv", no_rise_examples)
    write_csv(OUT_DIR / "study_index_boundary_top100.csv", boundary_examples)

    month_summary = {month: summarize(items) for month, items in sorted(by_month.items())}
    bucket_summary = {name: summarize(items) for name, items in sorted(by_bucket.items())}
    summary = {
        "source": str(SRC_DIR / "trade_backtest.json"),
        "total": summarize(rows),
        "by_month": month_summary,
        "by_bucket": bucket_summary,
        "files": {
            "all_csv": str(OUT_DIR / "all_b1_learning_samples.csv"),
            "all_json": str(OUT_DIR / "all_b1_learning_samples.json"),
            "by_month_dir": str(OUT_DIR / "by_month"),
            "by_bucket_dir": str(OUT_DIR / "by_bucket"),
        },
    }
    (OUT_DIR / "learning_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# B1 全量学习样本库",
        "",
        "这份样本库不做精选排序，也不按评分筛掉样本。目标是学习交易系统里的完整路径：为什么触发、如何入场、止损在哪里、离场怎么发生、最后收益如何。",
        "",
        "## 总览",
        "",
        f"- 全量样本：{summary['total']['count']} 笔",
        f"- 胜率：{summary['total']['win_rate_pct']}%",
        f"- 平均收益：{summary['total']['avg_return_pct']}%",
        f"- 中位收益：{summary['total']['median_return_pct']}%",
        f"- 最好/最差：{summary['total']['best_return_pct']}% / {summary['total']['worst_return_pct']}%",
        "",
        "## 月度分布",
        "",
        "| 月份 | 样本 | 胜率 | 平均收益 | 中位收益 | 最好 | 最差 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for month, stats in month_summary.items():
        lines.append(
            f"| {month} | {stats['count']} | {stats['win_rate_pct']}% | {stats['avg_return_pct']}% | {stats['median_return_pct']}% | {stats['best_return_pct']}% | {stats['worst_return_pct']}% |"
        )
    lines.extend(["", "## 学习分类", "", "| 分类 | 样本 | 胜率 | 平均收益 | 用途 |", "| --- | ---: | ---: | ---: | --- |"])
    purpose = {
        "正例-强收益": "看什么样的 B1 能走出空间，以及如何放飞/离场",
        "正例-小赚或防守成功": "看系统如何用半仓放飞、破线离场保住利润",
        "反例-止损": "训练止损执行，尤其是跳空破止损和盘中破止损",
        "反例-没涨就走": "训练 3 天不涨纪律",
        "边界-盈转亏": "训练赢转亏必走",
        "边界-不亏或小亏": "看交易系统如何减少无效持仓",
    }
    for name, stats in bucket_summary.items():
        lines.append(f"| {name} | {stats['count']} | {stats['win_rate_pct']}% | {stats['avg_return_pct']}% | {purpose.get(name, '')} |")
    lines.extend(
        [
            "",
            "## 文件",
            "",
            f"- 全量 CSV：`{OUT_DIR / 'all_b1_learning_samples.csv'}`",
            f"- 全量 JSON：`{OUT_DIR / 'all_b1_learning_samples.json'}`",
            f"- 按月份拆分：`{OUT_DIR / 'by_month'}`",
            f"- 按学习分类拆分：`{OUT_DIR / 'by_bucket'}`",
            f"- 强收益索引：`{OUT_DIR / 'study_index_positive_top100.csv'}`",
            f"- 止损反例索引：`{OUT_DIR / 'study_index_stoploss_top100.csv'}`",
            f"- 没涨就走索引：`{OUT_DIR / 'study_index_no_rise_top100.csv'}`",
            f"- 边界样本索引：`{OUT_DIR / 'study_index_boundary_top100.csv'}`",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"out_dir": str(OUT_DIR), "count": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

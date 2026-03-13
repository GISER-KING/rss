"""
6.6节 实验结果分析脚本

读取专家评分CSV，计算各维度均值/标准差，输出论文格式表格

用法：
    python -m app.scripts.analyze_results expert_scores.csv
"""

import sys
import csv
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime

from loguru import logger


def load_expert_scores(csv_path: str) -> List[Dict]:
    """加载专家评分CSV"""
    records = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                record = {
                    "id": int(row.get("序号", 0)),
                    "task_type": row.get("任务类型", ""),
                    "accuracy": float(row.get("准确性(1-5)", 0)),
                    "completeness": float(row.get("完整性(1-5)", 0)),
                    "relevance": float(row.get("相关性(1-5)", 0)),
                    "readability": float(row.get("可读性(1-5)", 0)),
                }
                records.append(record)
            except (ValueError, TypeError):
                continue
    return records


def compute_stats(values: List[float]) -> Dict[str, float]:
    """计算均值和标准差"""
    n = len(values)
    if n == 0:
        return {"mean": 0, "std": 0, "count": 0}
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    std = variance ** 0.5
    return {"mean": round(mean, 2), "std": round(std, 2), "count": n}


def analyze_and_report(csv_path: str):
    """分析专家评分并生成报告"""
    records = load_expert_scores(csv_path)

    if not records:
        logger.error("未能加载任何评分记录")
        return

    logger.info(f"加载了 {len(records)} 条评分记录")

    dimensions = [
        ("accuracy", "准确性"),
        ("completeness", "完整性"),
        ("relevance", "相关性"),
        ("readability", "可读性"),
    ]

    # ── 总体统计 ──
    logger.info("\n" + "=" * 50)
    logger.info("总体评分统计")
    logger.info("=" * 50)

    overall_stats = {}
    all_scores = []
    for dim_key, dim_name in dimensions:
        values = [r[dim_key] for r in records if r[dim_key] > 0]
        stats = compute_stats(values)
        overall_stats[dim_name] = stats
        all_scores.extend(values)
        logger.info(f"{dim_name}: 均值={stats['mean']:.1f}, 标准差={stats['std']:.1f} (n={stats['count']})")

    total_stats = compute_stats(all_scores)
    logger.info(f"总体: 均值={total_stats['mean']:.1f}, 标准差={total_stats['std']:.1f}")

    # ── 论文表格格式输出 ──
    logger.info("\n论文表格（Markdown格式）:")
    logger.info("| 评估维度 | 平均分 | 标准差 |")
    logger.info("|---------|--------|--------|")
    for dim_key, dim_name in dimensions:
        s = overall_stats[dim_name]
        logger.info(f"| {dim_name} | {s['mean']:.1f} | {s['std']:.1f} |")
    logger.info(f"| **总体** | **{total_stats['mean']:.1f}** | **{total_stats['std']:.1f}** |")

    # ── 按任务类型分组 ──
    task_types = list(set(r["task_type"] for r in records if r["task_type"]))
    if task_types:
        logger.info("\n" + "=" * 50)
        logger.info("按任务类型分组统计")
        logger.info("=" * 50)

        for task_type in sorted(task_types):
            type_records = [r for r in records if r["task_type"] == task_type]
            logger.info(f"\n{task_type} (n={len(type_records)}):")
            for dim_key, dim_name in dimensions:
                values = [r[dim_key] for r in type_records if r[dim_key] > 0]
                stats = compute_stats(values)
                logger.info(f"  {dim_name}: {stats['mean']:.1f} ± {stats['std']:.1f}")

    # ── 保存JSON结果 ──
    output_dir = Path(csv_path).parent
    output_file = output_dir / "eval_expert_analysis.json"

    analysis = {
        "experiment": "专家评审结果分析",
        "timestamp": datetime.now().isoformat(),
        "total_records": len(records),
        "overall": {
            dim_name: overall_stats[dim_name] for _, dim_name in dimensions
        },
        "overall_total": total_stats,
    }

    if task_types:
        analysis["by_task_type"] = {}
        for task_type in sorted(task_types):
            type_records = [r for r in records if r["task_type"] == task_type]
            analysis["by_task_type"][task_type] = {
                dim_name: compute_stats([r[dim_key] for r in type_records if r[dim_key] > 0])
                for dim_key, dim_name in dimensions
            }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    logger.info(f"\n分析结果已保存到: {output_file}")


def main():
    if len(sys.argv) < 2:
        # 默认路径
        default_path = Path(__file__).parent.parent.parent / "data" / "expert_evaluation_form.csv"
        if default_path.exists():
            csv_path = str(default_path)
        else:
            print(f"用法: python -m app.scripts.analyze_results <评分CSV路径>")
            print(f"默认路径 {default_path} 不存在")
            return
    else:
        csv_path = sys.argv[1]

    analyze_and_report(csv_path)


if __name__ == "__main__":
    main()

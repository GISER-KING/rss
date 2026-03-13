"""
6.6节 系统性能评估脚本

包含三个评估实验：
1. 检索性能评估（单流 vs 双流，延迟+准确率）
2. 任务分类准确率评估
3. 专家评审表生成

用法：
    python -m app.scripts.evaluate retrieval     # 运行检索性能评估
    python -m app.scripts.evaluate classification # 运行任务分类评估
    python -m app.scripts.evaluate expert_form    # 生成专家评审表
    python -m app.scripts.evaluate all            # 运行全部
"""

import sys
import json
import time
import csv
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger
from app.core import config


def load_test_queries() -> List[Dict[str, Any]]:
    """加载测试查询集"""
    queries_file = Path(__file__).parent.parent.parent / "data" / "test_queries.json"
    with open(queries_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["queries"]


# ─────────────────────────────────────────────────────────
# 实验1：检索性能评估
# ─────────────────────────────────────────────────────────

def evaluate_retrieval():
    """
    对比单流检索 vs 双流检索的延迟和准确率

    评估指标：
    - 平均延迟(ms)
    - Precision@K (K=5, 10, 20)
    """
    from app.agents.river_agent import build_kb, build_dual_stream_kb, _get_shared_embedder

    logger.info("=" * 60)
    logger.info("实验1：检索性能评估")
    logger.info("=" * 60)

    queries = load_test_queries()
    embedder = _get_shared_embedder()

    # 构建知识库
    logger.info("构建单流知识库...")
    single_kb = build_kb(embedder)

    logger.info("构建双流知识库...")
    dual_kb = build_dual_stream_kb(embedder)

    results = {
        "single_stream": {"latencies": [], "top_5": [], "top_10": [], "top_20": []},
        "dual_stream": {"latencies": [], "top_5": [], "top_10": [], "top_20": []},
    }

    for query_item in queries:
        query = query_item["query"]
        intent = query_item.get("intent", "mixed")

        # 单流检索
        start = time.perf_counter()
        try:
            if hasattr(single_kb, 'vector_db') and single_kb.vector_db:
                single_results = single_kb.vector_db.search(query, limit=20)
                if hasattr(single_results, '__len__'):
                    n_results = len(single_results) if single_results else 0
                else:
                    single_results = list(single_results) if single_results else []
                    n_results = len(single_results)
            else:
                n_results = 0
        except Exception:
            n_results = 0
        single_latency = (time.perf_counter() - start) * 1000
        results["single_stream"]["latencies"].append(single_latency)

        # 双流检索
        start = time.perf_counter()
        try:
            dual_results = dual_kb.hybrid_retrieval(query, top_k=20)
            n_dual = len(dual_results)
        except Exception:
            dual_results = []
            n_dual = 0
        dual_latency = (time.perf_counter() - start) * 1000
        results["dual_stream"]["latencies"].append(dual_latency)

        # 计算各Top-K的结果数（作为精度的代理指标）
        for k_val, k_key in [(5, "top_5"), (10, "top_10"), (20, "top_20")]:
            results["single_stream"][k_key].append(min(n_results, k_val))
            results["dual_stream"][k_key].append(min(n_dual, k_val))

    # 输出结果表格
    logger.info("\n检索性能对比结果:")
    logger.info("-" * 70)
    logger.info(f"{'检索方法':<12} {'Top-K':<8} {'平均延迟(ms)':<15} {'平均召回数':<12}")
    logger.info("-" * 70)

    for method_name, method_key in [("文档流单独", "single_stream"), ("双流RAG", "dual_stream")]:
        avg_latency = sum(results[method_key]["latencies"]) / len(results[method_key]["latencies"])
        for k_val, k_key in [(5, "top_5"), (10, "top_10"), (20, "top_20")]:
            avg_recall = sum(results[method_key][k_key]) / len(results[method_key][k_key])
            logger.info(f"{method_name:<12} {k_val:<8} {avg_latency:<15.1f} {avg_recall:<12.1f}")

    # 保存详细结果
    output_file = Path(__file__).parent.parent.parent / "data" / "eval_retrieval.json"
    summary = {
        "experiment": "检索性能评估",
        "timestamp": datetime.now().isoformat(),
        "query_count": len(queries),
        "results": {}
    }
    for method_key in ["single_stream", "dual_stream"]:
        avg_latency = sum(results[method_key]["latencies"]) / len(results[method_key]["latencies"])
        summary["results"][method_key] = {
            "avg_latency_ms": round(avg_latency, 2),
            "top_5_avg": round(sum(results[method_key]["top_5"]) / len(results[method_key]["top_5"]), 2),
            "top_10_avg": round(sum(results[method_key]["top_10"]) / len(results[method_key]["top_10"]), 2),
            "top_20_avg": round(sum(results[method_key]["top_20"]) / len(results[method_key]["top_20"]), 2),
        }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    logger.info(f"\n详细结果已保存到: {output_file}")


# ─────────────────────────────────────────────────────────
# 实验2：任务分类准确率评估
# ─────────────────────────────────────────────────────────

def evaluate_task_classification():
    """
    评估任务分类准确率

    使用SolutionDatabase的关键词匹配进行分类，
    对比test_queries.json中的标注结果
    """
    from app.agents.solution_space import SolutionDatabase
    from app.agents.river_agent import _get_shared_embedder

    logger.info("=" * 60)
    logger.info("实验2：任务分类准确率评估")
    logger.info("=" * 60)

    queries = load_test_queries()
    embedder = _get_shared_embedder()
    solution_db = SolutionDatabase(embedder=embedder)  # 语义相似度匹配

    # 任务类型列表
    task_types = ["岸线知识问答", "岸线统计分析", "岸线类型识别", "水体提取", "区域对比分析"]

    correct = 0
    total = len(queries)
    per_class = {t: {"tp": 0, "fp": 0, "fn": 0, "total": 0} for t in task_types}
    confusion = {t: {t2: 0 for t2 in task_types} for t in task_types}

    results_detail = []

    for query_item in queries:
        query = query_item["query"]
        gold_type = query_item["task_type"]

        # 分类
        solution = solution_db.retrieve_solution(query)
        pred_type = solution.get("task_type", "岸线知识问答")

        is_correct = pred_type == gold_type
        if is_correct:
            correct += 1

        # 更新统计
        per_class[gold_type]["total"] += 1
        if is_correct:
            per_class[gold_type]["tp"] += 1
        else:
            per_class[gold_type]["fn"] += 1
            per_class[pred_type]["fp"] += 1

        # 混淆矩阵
        if gold_type in confusion and pred_type in confusion[gold_type]:
            confusion[gold_type][pred_type] += 1

        results_detail.append({
            "query": query,
            "gold": gold_type,
            "predicted": pred_type,
            "correct": is_correct,
        })

    # 输出结果
    accuracy = correct / total if total > 0 else 0
    logger.info(f"\n总体准确率: {correct}/{total} = {accuracy:.1%}")

    logger.info(f"\n{'任务类型':<12} {'查询数':<8} {'正确分类':<10} {'准确率':<10}")
    logger.info("-" * 45)
    for t in task_types:
        tp = per_class[t]["tp"]
        tot = per_class[t]["total"]
        acc = tp / tot if tot > 0 else 0
        logger.info(f"{t:<12} {tot:<8} {tp:<10} {acc:<10.0%}")

    # 混淆矩阵
    logger.info(f"\n混淆矩阵 (行=真实, 列=预测):")
    header = f"{'':>12}" + "".join(f"{t[:4]:>8}" for t in task_types)
    logger.info(header)
    for gold in task_types:
        row = f"{gold[:8]:>12}" + "".join(f"{confusion[gold][pred]:>8}" for pred in task_types)
        logger.info(row)

    # 保存结果
    output_file = Path(__file__).parent.parent.parent / "data" / "eval_classification.json"
    summary = {
        "experiment": "任务分类准确率评估",
        "timestamp": datetime.now().isoformat(),
        "total_queries": total,
        "correct": correct,
        "accuracy": round(accuracy, 4),
        "per_class": {
            t: {
                "total": per_class[t]["total"],
                "correct": per_class[t]["tp"],
                "accuracy": round(per_class[t]["tp"] / per_class[t]["total"], 4) if per_class[t]["total"] > 0 else 0,
            }
            for t in task_types
        },
        "confusion_matrix": confusion,
        "details": results_detail,
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    logger.info(f"\n详细结果已保存到: {output_file}")


# ─────────────────────────────────────────────────────────
# 实验3：生成专家评审表
# ─────────────────────────────────────────────────────────

def generate_expert_form():
    """
    对50个查询运行系统，生成CSV评审表供5位专家评分

    评分维度（1-5分）：
    1. 准确性：回答是否正确
    2. 完整性：回答是否全面
    3. 相关性：回答是否切题
    4. 可读性：回答是否清晰易懂
    """
    from app.agents.river_agent import build_enhanced_agent, enhanced_stream_agent

    logger.info("=" * 60)
    logger.info("实验3：生成专家评审表")
    logger.info("=" * 60)

    queries = load_test_queries()

    # 构建Agent
    agent, dual_kb, solution_db = build_enhanced_agent(
        api_base_url=config.API_BASE_URL, api_key=config.API_KEY, mode="agent"
    )

    responses = []

    for i, query_item in enumerate(queries):
        query = query_item["query"]
        logger.info(f"[{i+1}/{len(queries)}] 运行查询: {query[:40]}...")

        # 收集完整回答
        full_content = ""
        try:
            for chunk in enhanced_stream_agent(
                agent, dual_kb, solution_db,
                query, session_id=f"eval_{i}"
            ):
                content = chunk.get("content", "")
                if content:
                    full_content += content
        except Exception as e:
            full_content = f"[ERROR] {str(e)}"
            logger.error(f"  查询失败: {e}")

        responses.append({
            "id": query_item["id"],
            "task_type": query_item["task_type"],
            "query": query,
            "response": full_content,
            "response_length": len(full_content),
        })
        logger.info(f"  回答长度: {len(full_content)}字")

    # 生成CSV评审表
    output_dir = Path(__file__).parent.parent.parent / "data"

    csv_file = output_dir / "expert_evaluation_form.csv"
    with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "序号", "任务类型", "用户查询", "系统回答",
            "准确性(1-5)", "完整性(1-5)", "相关性(1-5)", "可读性(1-5)", "备注"
        ])
        for r in responses:
            writer.writerow([
                r["id"], r["task_type"], r["query"],
                r["response"][:2000],  # 截断过长回答
                "", "", "", "", ""  # 空评分列
            ])

    logger.info(f"\nCSV评审表已保存到: {csv_file}")

    # 同时保存完整回答的JSON
    json_file = output_dir / "expert_evaluation_responses.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(responses, f, ensure_ascii=False, indent=2)
    logger.info(f"完整回答JSON已保存到: {json_file}")


# ─────────────────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="RSS-Agent 6.6节性能评估")
    parser.add_argument(
        "experiment",
        choices=["retrieval", "classification", "expert_form", "all"],
        help="要运行的实验"
    )
    args = parser.parse_args()

    if args.experiment in ("retrieval", "all"):
        evaluate_retrieval()

    if args.experiment in ("classification", "all"):
        evaluate_task_classification()

    if args.experiment in ("expert_form", "all"):
        generate_expert_form()


if __name__ == "__main__":
    main()

"""
6.5节 应用案例测试脚本
直接调用后端函数运行5个典型案例，输出完整回答和引用来源
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.agents.river_agent import (
    build_enhanced_agent,
    enhanced_stream_agent,
)
from app.core import config
from loguru import logger


# 6.5节的5个典型应用案例
TEST_CASES = [
    {
        "id": 1,
        "title": "案例1：概念解释（文档流检索）",
        "query": "什么是生态岸线？请详细解释其定义、特征和在河流管理中的重要性。",
        "mode": "chat",
        "expected_behavior": "从学术文献中检索生态岸线定义，α偏向文档流(0.3)",
    },
    {
        "id": 2,
        "title": "案例2：数据查询（数据流检索 + 工具调用）",
        "query": "朝阳区有多少公里自然岸线？请给出具体数据。",
        "mode": "agent",
        "expected_behavior": "α偏向数据流(0.7)，调用query_shoreline_database工具",
    },
    {
        "id": 3,
        "title": "案例3：统计分析（工具链调用）",
        "query": "统计各区域的岸线类型分布，计算各类型岸线的总长度和占比。",
        "mode": "agent",
        "expected_behavior": "调用query_shoreline_database → calculate_statistics工具链",
    },
    {
        "id": 4,
        "title": "案例4：水体提取（算法工具调用）",
        "query": "请提取这张遥感影像中的水体边界。影像路径：data/uploads/images/sample.tif",
        "mode": "agent",
        "expected_behavior": "调用extract_water_body工具",
    },
    {
        "id": 5,
        "title": "案例5：综合评估（混合检索）",
        "query": "请综合评估朝阳区自然岸线的生态价值，结合文献理论和实际数据进行分析。",
        "mode": "agent",
        "expected_behavior": "混合检索α=0.5，同时使用文档流理论+数据流事实",
    },
]


def run_single_case(case: dict) -> dict:
    """运行单个测试案例"""
    logger.info(f"\n{'='*60}")
    logger.info(f"运行 {case['title']}")
    logger.info(f"查询: {case['query']}")
    logger.info(f"模式: {case['mode']}")
    logger.info(f"{'='*60}")

    # 构建增强Agent
    agent, dual_kb, solution_db = build_enhanced_agent(
        api_base_url=config.API_BASE_URL,
        api_key=config.API_KEY,
        mode=case["mode"]
    )

    # 收集流式输出
    full_content = ""
    all_references = []

    try:
        for chunk in enhanced_stream_agent(
            agent, dual_kb, solution_db,
            case["query"],
            session_id=f"test_case_{case['id']}"
        ):
            content = chunk.get("content", "")
            if content:
                full_content += content
                print(content, end="", flush=True)

            refs = chunk.get("references", [])
            if refs:
                all_references.extend(refs)

    except Exception as e:
        logger.error(f"案例执行出错: {e}")
        full_content = f"[ERROR] {str(e)}"

    print()  # 换行

    result = {
        "case_id": case["id"],
        "title": case["title"],
        "query": case["query"],
        "mode": case["mode"],
        "response": full_content,
        "references": all_references,
        "reference_count": len(all_references),
        "response_length": len(full_content),
    }

    # 打印引用信息
    if all_references:
        logger.info(f"\n引用来源 ({len(all_references)}条):")
        for i, ref in enumerate(all_references, 1):
            meta = ref.get("meta_data", {})
            stream = meta.get("stream_type", "unknown")
            source = meta.get("file_name") or meta.get("region") or "未知"
            logger.info(f"  [{stream}] {source}")

    return result


def run_all_cases():
    """运行全部测试案例"""
    logger.info("=" * 60)
    logger.info("RSS-Agent 6.5节 应用案例测试")
    logger.info(f"时间: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    results = []
    for case in TEST_CASES:
        result = run_single_case(case)
        results.append(result)
        logger.info(f"✓ {case['title']} 完成 (回答长度: {result['response_length']}字)")

    # 保存结果
    output_dir = Path(__file__).parent.parent.parent / "data"
    output_file = output_dir / "test_cases_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f"\n结果已保存到: {output_file}")

    # 生成文本报告
    report_file = output_dir / "test_cases_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# RSS-Agent 6.5节 应用案例测试报告\n\n")
        f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for result in results:
            f.write(f"## {result['title']}\n\n")
            f.write(f"**用户查询**: {result['query']}\n\n")
            f.write(f"**运行模式**: {result['mode']}\n\n")
            f.write(f"**系统回答**:\n\n{result['response']}\n\n")
            if result['references']:
                f.write(f"**知识引用** ({result['reference_count']}条):\n\n")
                for ref in result['references']:
                    meta = ref.get("meta_data", {})
                    stream = meta.get("stream_type", "unknown")
                    source = meta.get("file_name") or meta.get("region") or "未知"
                    f.write(f"- [{stream}] {source}\n")
            f.write("\n---\n\n")

    logger.info(f"报告已保存到: {report_file}")

    # 汇总
    logger.info("\n" + "=" * 60)
    logger.info("测试汇总:")
    for r in results:
        status = "✓" if r["response_length"] > 0 else "✗"
        logger.info(f"  {status} {r['title']}: {r['response_length']}字, {r['reference_count']}条引用")


if __name__ == "__main__":
    run_all_cases()

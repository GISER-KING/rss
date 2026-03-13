"""
岸线识别结果数据导入脚本
用于将第4章、第5章的岸线识别结果导入到双流RAG系统
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.agents.river_agent import build_dual_stream_kb, ingest_shoreline_results
from loguru import logger


def load_json_file(file_path: str) -> List[Dict[str, Any]]:
    """
    从JSON文件加载岸线数据

    Args:
        file_path: JSON文件路径

    Returns:
        岸线数据列表
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 支持两种格式：直接列表或包含results字段的字典
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'results' in data:
            return data['results']
        else:
            logger.error(f"不支持的JSON格式: {type(data)}")
            return []

    except Exception as e:
        logger.error(f"加载JSON文件失败: {e}")
        return []


def validate_shoreline_data(data: List[Dict[str, Any]]) -> bool:
    """
    验证岸线数据格式

    必需字段：region, shoreline_type, length_km, confidence, percentage, source_chapter
    """
    required_fields = ["region", "shoreline_type", "length_km", "confidence", "source_chapter"]

    for i, item in enumerate(data):
        for field in required_fields:
            if field not in item:
                logger.error(f"第{i+1}条数据缺少必需字段: {field}")
                return False

    logger.info(f"数据验证通过: {len(data)}条记录")
    return True


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='导入岸线识别结果数据')
    parser.add_argument('json_file', type=str, help='JSON数据文件路径')
    parser.add_argument('--validate-only', action='store_true', help='仅验证数据格式，不导入')

    args = parser.parse_args()

    # 1. 加载数据
    logger.info(f"正在加载数据文件: {args.json_file}")
    data = load_json_file(args.json_file)

    if not data:
        logger.error("未能加载任何数据")
        return

    # 2. 验证数据
    if not validate_shoreline_data(data):
        logger.error("数据验证失败")
        return

    if args.validate_only:
        logger.info("验证完成，退出")
        return

    # 3. 构建双流知识库
    logger.info("正在初始化双流知识库...")
    dual_kb = build_dual_stream_kb()

    # 4. 导入数据
    logger.info("正在导入岸线数据...")
    result = ingest_shoreline_results(dual_kb, data)

    if result['success']:
        logger.success(result['message'])
    else:
        logger.error(result['message'])


if __name__ == "__main__":
    main()

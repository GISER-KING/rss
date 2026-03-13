"""
岸线分析工具集
提供岸线分类、统计分析、数据查询等功能
"""

from typing import Dict, Any, List, Optional
from loguru import logger
from ..core.db import get_session
from sqlmodel import select
from ..db.models import ShorelineResult


def classify_shoreline(boundary_coords: List[List[float]]) -> Dict[str, Any]:
    """
    岸线分类工具（模拟实现）

    在实际系统中，这里会调用第4章的岸线识别算法

    Args:
        boundary_coords: 边界坐标列表 [[lon1, lat1], [lon2, lat2], ...]

    Returns:
        分类结果字典
    """
    logger.info(f"正在分类岸线，边界点数: {len(boundary_coords)}")

    # 模拟分类结果
    result = {
        "success": True,
        "shoreline_types": [
            {
                "type": "自然岸线",
                "length_km": 8.5,
                "percentage": 42.5,
                "confidence": 0.89
            },
            {
                "type": "人工岸线",
                "length_km": 11.5,
                "percentage": 57.5,
                "confidence": 0.92
            }
        ],
        "total_length_km": 20.0,
        "message": "岸线分类完成"
    }

    return result


def query_shoreline_database(
    region: Optional[str] = None,
    shoreline_type: Optional[str] = None,
    min_length: Optional[float] = None
) -> Dict[str, Any]:
    """
    查询岸线数据库

    从ShorelineResult表中查询符合条件的岸线数据

    Args:
        region: 区域名称（可选）
        shoreline_type: 岸线类型（可选）
        min_length: 最小长度（可选）

    Returns:
        查询结果字典
    """
    logger.info(f"查询岸线数据: region={region}, type={shoreline_type}, min_length={min_length}")

    try:
        with get_session() as session:
            # 构建查询
            query = select(ShorelineResult)

            if region:
                query = query.where(ShorelineResult.region == region)

            if shoreline_type:
                query = query.where(ShorelineResult.shoreline_type == shoreline_type)

            if min_length is not None:
                query = query.where(ShorelineResult.length_km >= min_length)

            # 执行查询
            results = session.exec(query).all()

            # 格式化结果
            data = []
            for r in results:
                data.append({
                    "region": r.region,
                    "shoreline_type": r.shoreline_type,
                    "length_km": r.length_km,
                    "confidence": r.confidence,
                    "percentage": r.percentage,
                    "source_chapter": r.source_chapter,
                    "description": r.description
                })

            return {
                "success": True,
                "count": len(data),
                "data": data,
                "message": f"查询到{len(data)}条记录"
            }

    except Exception as e:
        logger.error(f"查询失败: {e}")
        return {
            "success": False,
            "count": 0,
            "data": [],
            "message": f"查询失败: {str(e)}"
        }


def calculate_statistics(
    region: Optional[str] = None,
    shoreline_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    统计分析工具

    对岸线数据进行统计分析。如果不提供参数，则统计所有数据。

    Args:
        region: 区域名称（可选），如果提供则只统计该区域的数据
        shoreline_type: 岸线类型（可选），如果提供则只统计该类型的数据

    Returns:
        统计结果字典，包含总长度、分类统计等信息
    """
    logger.info(f"正在进行统计分析: region={region}, type={shoreline_type}")

    try:
        # 先查询数据
        with get_session() as session:
            query = select(ShorelineResult)

            if region:
                query = query.where(ShorelineResult.region == region)

            if shoreline_type:
                query = query.where(ShorelineResult.shoreline_type == shoreline_type)

            results = session.exec(query).all()

            # 转换为字典列表
            data = [
                {
                    "region": r.region,
                    "shoreline_type": r.shoreline_type,
                    "length_km": r.length_km,
                    "confidence": r.confidence,
                    "percentage": r.percentage,
                    "source_chapter": r.source_chapter,
                    "description": r.description
                }
                for r in results
            ]

        if not data:
            return {
                "success": False,
                "message": "没有数据可供分析"
            }

        # 计算总长度
        total_length = sum(item.get("length_km", 0) for item in data)

        # 按类型分组统计
        type_stats = {}
        for item in data:
            shoreline_type = item.get("shoreline_type", "未知")
            length = item.get("length_km", 0)

            if shoreline_type not in type_stats:
                type_stats[shoreline_type] = {
                    "count": 0,
                    "total_length": 0,
                    "avg_confidence": []
                }

            type_stats[shoreline_type]["count"] += 1
            type_stats[shoreline_type]["total_length"] += length
            type_stats[shoreline_type]["avg_confidence"].append(
                item.get("confidence", 0)
            )

        # 计算平均置信度和百分比
        for shoreline_type, stats in type_stats.items():
            stats["percentage"] = (stats["total_length"] / total_length * 100) if total_length > 0 else 0
            stats["avg_confidence"] = sum(stats["avg_confidence"]) / len(stats["avg_confidence"]) if stats["avg_confidence"] else 0

        # 按区域分组统计
        region_stats = {}
        for item in data:
            region = item.get("region", "未知")
            length = item.get("length_km", 0)

            if region not in region_stats:
                region_stats[region] = {
                    "count": 0,
                    "total_length": 0
                }

            region_stats[region]["count"] += 1
            region_stats[region]["total_length"] += length

        return {
            "success": True,
            "total_length_km": round(total_length, 2),
            "total_records": len(data),
            "by_type": {
                k: {
                    "count": v["count"],
                    "total_length_km": round(v["total_length"], 2),
                    "percentage": round(v["percentage"], 1),
                    "avg_confidence": round(v["avg_confidence"], 2)
                }
                for k, v in type_stats.items()
            },
            "by_region": {
                k: {
                    "count": v["count"],
                    "total_length_km": round(v["total_length"], 2)
                }
                for k, v in region_stats.items()
            },
            "message": "统计分析完成"
        }

    except Exception as e:
        logger.error(f"统计分析失败: {e}")
        return {
            "success": False,
            "message": f"统计分析失败: {str(e)}"
        }

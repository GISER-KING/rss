"""
双流RAG知识索引机制
基于RS-Agent论文(arxiv 2406.07089v2)的双流检索增强生成实现

文档流(Document Stream): 索引学术文献、技术报告等非结构化文本
数据流(Data Stream): 索引岸线识别结果等结构化数据
"""

import json
from typing import List, Dict, Any, Tuple
from pathlib import Path
import numpy as np
from loguru import logger


class DualStreamKnowledgeBase:
    """
    双流知识库：文档流 + 数据流

    核心创新：
    1. 异构数据统一索引：将结构化数据转换为自然语言描述后索引
    2. 动态权重分配：根据查询意图自适应调整两个流的检索权重
    3. 混合检索策略：并行检索后按相关度融合结果
    """

    def __init__(self, vector_db, embedder):
        """
        初始化双流知识库

        Args:
            vector_db: LanceDB向量数据库实例
            embedder: 文本嵌入模型(BGE-small-zh-v1.5)
        """
        self.vector_db = vector_db
        self.embedder = embedder

        # 两个独立的collection
        self.doc_collection_name = "literature_documents"
        self.data_collection_name = "shoreline_results"

        logger.info("双流知识库初始化完成")

    def _get_or_create_table(self, collection_name: str, data: list):
        """获取或创建LanceDB表"""
        try:
            table = self.vector_db.open_table(collection_name)
            table.add(data)
        except Exception:
            # 表不存在，创建新表
            import pyarrow as pa
            table = self.vector_db.create_table(collection_name, data=data)
        return table

    def ingest_document_stream(self, pdf_path: str, chunk_size: int = 500) -> int:
        """
        文档流摄取：索引学术文献

        处理流程：
        1. PDF解析与分块
        2. 文本向量化
        3. 存储到doc_collection

        Args:
            pdf_path: PDF文件路径
            chunk_size: 分块大小(字符数)

        Returns:
            索引的文档块数量
        """
        from ..utils.pdf import load_pdf_chunks

        logger.info(f"开始摄取文档流: {pdf_path}")

        # 复用现有的PDF解析逻辑
        chunks = load_pdf_chunks(pdf_path, chunk_size=chunk_size, chunk_overlap=50)

        if not chunks:
            logger.warning(f"未能从 {pdf_path} 提取到文本块")
            return 0

        # 准备向量化数据
        documents = []
        for i, chunk in enumerate(chunks):
            # 生成嵌入向量
            embedding = self.embedder.get_embedding(chunk["text"])

            documents.append({
                "id": f"doc_{Path(pdf_path).stem}_{i}",
                "text": chunk["text"],
                "vector": embedding,
                "metadata": {
                    "source": pdf_path,
                    "page": chunk.get("page", -1),
                    "chunk_index": i,
                    "stream_type": "document"
                }
            })

        # 存储到文档流collection
        self._get_or_create_table(self.doc_collection_name, documents)

        logger.info(f"文档流摄取完成: {len(documents)} 个文本块")
        return len(documents)

    def ingest_data_stream(self, shoreline_results: List[Dict[str, Any]]) -> int:
        """
        数据流摄取：索引岸线识别结果

        核心创新：结构化数据的自然语言转换
        将JSON格式的岸线数据转换为可检索的自然语言描述

        示例输入：
        {
            "region": "朝阳区",
            "shoreline_type": "自然岸线",
            "length_km": 12.5,
            "confidence": 0.92,
            "percentage": 35.7,
            "source_chapter": "第4章"
        }

        转换为：
        "朝阳区的自然岸线长度为12.5公里，占该区域岸线总长度的35.7%，
         识别置信度为0.92。该数据来源于第4章的岸线识别结果。"

        Args:
            shoreline_results: 岸线识别结果列表

        Returns:
            索引的数据条目数量
        """
        logger.info(f"开始摄取数据流: {len(shoreline_results)} 条记录")

        documents = []
        for i, result in enumerate(shoreline_results):
            # 结构化数据 -> 自然语言描述
            nl_description = self._convert_to_natural_language(result)

            # 生成嵌入向量
            embedding = self.embedder.get_embedding(nl_description)

            documents.append({
                "id": f"data_{result.get('region', 'unknown')}_{result.get('shoreline_type', 'unknown')}_{i}",
                "text": nl_description,
                "vector": embedding,
                "metadata": {
                    "region": result.get("region"),
                    "shoreline_type": result.get("shoreline_type"),
                    "length_km": result.get("length_km"),
                    "confidence": result.get("confidence"),
                    "percentage": result.get("percentage"),
                    "source_chapter": result.get("source_chapter"),
                    "stream_type": "data",
                    "raw_data": json.dumps(result, ensure_ascii=False)
                }
            })

        # 存储到数据流collection
        self._get_or_create_table(self.data_collection_name, documents)

        logger.info(f"数据流摄取完成: {len(documents)} 条记录")
        return len(documents)

    def _convert_to_natural_language(self, data: Dict[str, Any]) -> str:
        """
        将结构化数据转换为自然语言描述

        设计原则：
        1. 保留关键数值信息
        2. 使用自然的语言表达
        3. 包含上下文信息(来源、置信度等)
        """
        region = data.get("region", "未知区域")
        shoreline_type = data.get("shoreline_type", "未知类型")
        length_km = data.get("length_km", 0)
        confidence = data.get("confidence", 0)
        percentage = data.get("percentage")
        source = data.get("source_chapter", "未知来源")

        pct_text = f"占该区域岸线总长度的{percentage:.1f}%，" if percentage is not None else ""

        description = (
            f"{region}的{shoreline_type}长度为{length_km:.2f}公里，"
            f"{pct_text}"
            f"识别置信度为{confidence:.2f}。"
            f"该数据来源于{source}的岸线识别结果。"
        )

        if data.get("description"):
            description += f" {data['description']}"

        return description

    def hybrid_retrieval(
        self,
        query: str,
        top_k: int = 10,
        alpha: float = None
    ) -> List[Dict[str, Any]]:
        """
        混合检索：动态权重分配的双流检索

        算法流程：
        1. 查询意图分析：判断查询偏向定量(数据)还是定性(文档)
        2. 并行检索：同时从两个collection检索
        3. 动态权重融合：根据意图调整两个流的权重
        4. 结果排序：按加权相关度分数排序

        权重计算公式(参考RS-Agent论文):
        score_final = α * score_data + (1-α) * score_doc

        其中α的取值策略：
        - 定量查询(包含数字、统计等关键词): α = 0.7
        - 定性查询(包含概念、原理等关键词): α = 0.3
        - 混合查询: α = 0.5

        Args:
            query: 用户查询
            top_k: 返回结果数量
            alpha: 数据流权重(0-1)，None表示自动推断

        Returns:
            融合后的检索结果列表
        """
        logger.info(f"混合检索: query='{query}', top_k={top_k}")

        # 步骤1: 查询意图分析
        if alpha is None:
            alpha = self._infer_query_intent(query)

        logger.debug(f"数据流权重α={alpha:.2f}, 文档流权重={1-alpha:.2f}")

        # 步骤2: 并行检索
        data_results = self._search_collection(
            self.data_collection_name,
            query,
            top_k=top_k
        )
        doc_results = self._search_collection(
            self.doc_collection_name,
            query,
            top_k=top_k
        )

        # 步骤3: 加权融合
        merged_results = []

        # 处理数据流结果
        for result in data_results:
            result["weighted_score"] = alpha * result["score"]
            result["stream_source"] = "数据流"
            merged_results.append(result)

        # 处理文档流结果
        for result in doc_results:
            result["weighted_score"] = (1 - alpha) * result["score"]
            result["stream_source"] = "文档流"
            merged_results.append(result)

        # 步骤4: 按加权分数排序并返回top_k
        merged_results.sort(key=lambda x: x["weighted_score"], reverse=True)
        final_results = merged_results[:top_k]

        logger.info(f"混合检索完成: 返回{len(final_results)}条结果")
        return final_results

    def _infer_query_intent(self, query: str) -> float:
        """
        推断查询意图，返回数据流权重α

        启发式规则：
        - 包含数字、统计、多少、占比等 -> 定量查询 (α=0.7)
        - 包含是什么、为什么、如何、原理等 -> 定性查询 (α=0.3)
        - 其他 -> 混合查询 (α=0.5)
        """
        quantitative_keywords = [
            "多少", "数量", "长度", "面积", "占比", "百分比",
            "统计", "总计", "平均", "最大", "最小", "公里", "米"
        ]

        qualitative_keywords = [
            "是什么", "为什么", "如何", "怎样", "原理", "定义",
            "概念", "特点", "意义", "作用", "影响", "方法"
        ]

        # 计算关键词匹配度
        quant_score = sum(1 for kw in quantitative_keywords if kw in query)
        qual_score = sum(1 for kw in qualitative_keywords if kw in query)

        if quant_score > qual_score:
            return 0.7  # 偏向数据流
        elif qual_score > quant_score:
            return 0.3  # 偏向文档流
        else:
            return 0.5  # 均衡

    def _search_collection(
        self,
        collection_name: str,
        query: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        在指定collection中执行向量检索

        Args:
            collection_name: collection名称
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            检索结果列表，每个结果包含text、score、metadata
        """
        try:
            table = self.vector_db.open_table(collection_name)
            query_vector = self.embedder.get_embedding(query)

            # 执行向量相似度搜索
            results = table.search(query_vector).limit(top_k).to_list()

            # 格式化结果
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "text": result.get("text", ""),
                    "score": 1.0 / (1.0 + result.get("_distance", 0)),  # LanceDB返回距离，转换为相似度
                    "metadata": result.get("metadata", {}),
                    "id": result.get("id", "")
                })

            return formatted_results

        except Exception as e:
            logger.error(f"检索collection '{collection_name}' 失败: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取知识库统计信息

        Returns:
            包含文档流和数据流统计的字典
        """
        try:
            doc_table = self.vector_db.open_table(self.doc_collection_name)
            data_table = self.vector_db.open_table(self.data_collection_name)

            return {
                "document_stream": {
                    "count": len(doc_table),
                    "collection": self.doc_collection_name
                },
                "data_stream": {
                    "count": len(data_table),
                    "collection": self.data_collection_name
                }
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                "document_stream": {"count": 0},
                "data_stream": {"count": 0}
            }

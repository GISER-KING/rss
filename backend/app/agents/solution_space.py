"""
任务感知的解决方案检索系统
基于RS-Agent论文(arxiv 2406.07089v2)的Task-Aware Retrieval实现

核心思想：
1. 维护一个解决方案数据库，存储常见任务的解决方案模板
2. 根据用户查询推断任务类型
3. 检索最相关的解决方案指导Agent执行
"""

from typing import Dict, List, Any
import numpy as np
from loguru import logger


class SolutionDatabase:
    """
    解决方案数据库

    存储预定义的任务解决方案，包括：
    - 任务描述
    - 所需工具
    - 执行步骤
    - 预期输出格式
    """

    # 解决方案模板库
    SOLUTIONS = {
        "岸线类型识别": {
            "task_type": "岸线类型识别",
            "description": "识别给定区域的岸线类型（自然岸线、人工岸线等）",
            "required_tools": ["extract_water_body", "classify_shoreline"],
            "execution_steps": [
                "1. 使用extract_water_body工具提取水体边界",
                "2. 使用classify_shoreline工具对边界进行分类",
                "3. 统计各类型岸线的长度和占比"
            ],
            "output_format": "返回岸线类型、长度(公里)、占比(%)的结构化数据",
            "example_queries": [
                "识别朝阳区的岸线类型",
                "这个区域有哪些类型的岸线",
                "分析温榆河的岸线构成"
            ]
        },

        "岸线统计分析": {
            "task_type": "岸线统计分析",
            "description": "对岸线数据进行统计分析，计算长度、占比等指标",
            "required_tools": ["query_shoreline_database", "calculate_statistics"],
            "execution_steps": [
                "1. 使用query_shoreline_database查询指定区域的岸线数据",
                "2. 使用calculate_statistics计算统计指标",
                "3. 生成可视化图表（如果需要）"
            ],
            "output_format": "返回统计表格和图表",
            "example_queries": [
                "朝阳区有多少公里自然岸线",
                "统计各区域的岸线长度",
                "计算人工岸线的占比"
            ]
        },

        "岸线知识问答": {
            "task_type": "岸线知识问答",
            "description": "回答关于岸线概念、原理、方法的问题",
            "required_tools": [],  # 仅使用RAG检索
            "execution_steps": [
                "1. 从文档流检索相关学术文献",
                "2. 综合多个文档片段生成答案",
                "3. 提供引用来源"
            ],
            "output_format": "自然语言回答，附带文献引用",
            "example_queries": [
                "什么是生态岸线",
                "岸线识别的主要方法有哪些",
                "自然岸线和人工岸线的区别"
            ]
        },

        "水体提取": {
            "task_type": "水体提取",
            "description": "从遥感影像中提取水体边界",
            "required_tools": ["extract_water_body"],
            "execution_steps": [
                "1. 接收影像路径或坐标",
                "2. 调用extract_water_body工具",
                "3. 返回水体边界矢量数据和可视化结果"
            ],
            "output_format": "返回边界坐标和叠加影像",
            "example_queries": [
                "提取这张影像的水体",
                "识别温榆河的边界",
                "从卫星图中提取河流"
            ]
        },

        "区域对比分析": {
            "task_type": "区域对比分析",
            "description": "对比多个区域的岸线特征",
            "required_tools": ["query_shoreline_database", "calculate_statistics"],
            "execution_steps": [
                "1. 查询各区域的岸线数据",
                "2. 计算对比指标（长度、占比、类型分布）",
                "3. 生成对比表格和图表"
            ],
            "output_format": "返回对比表格和可视化图表",
            "example_queries": [
                "对比朝阳区和海淀区的岸线",
                "哪个区域的自然岸线最多",
                "分析各区域岸线的差异"
            ]
        }
    }

    def __init__(self, embedder=None):
        """
        初始化解决方案数据库

        Args:
            embedder: 文本嵌入模型，用于语义检索
        """
        self.embedder = embedder
        self.solutions = self.SOLUTIONS

        # 预计算解决方案的嵌入向量（用于语义检索）
        if self.embedder:
            self._build_solution_embeddings()

    def _build_solution_embeddings(self):
        """预计算所有解决方案的嵌入向量"""
        self.solution_embeddings = {}

        for task_type, solution in self.solutions.items():
            # 将解决方案的关键信息拼接成文本
            text = f"{solution['description']} {' '.join(solution['example_queries'])}"
            embedding = self.embedder.get_embedding(text)
            self.solution_embeddings[task_type] = embedding

        logger.info(f"已构建{len(self.solution_embeddings)}个解决方案的嵌入向量")

    def retrieve_solution(self, user_query: str, top_k: int = 1) -> Dict[str, Any]:
        """
        检索最相关的解决方案

        使用语义相似度匹配用户查询和解决方案

        Args:
            user_query: 用户查询
            top_k: 返回前k个最相关的解决方案

        Returns:
            最相关的解决方案字典
        """
        if not self.embedder:
            # 如果没有嵌入器，使用关键词匹配
            return self._keyword_based_retrieval(user_query)

        # 语义检索
        query_embedding = self.embedder.get_embedding(user_query)

        # 计算与所有解决方案的相似度
        similarities = {}
        for task_type, solution_embedding in self.solution_embeddings.items():
            similarity = self._cosine_similarity(query_embedding, solution_embedding)
            similarities[task_type] = similarity

        # 排序并返回top_k
        sorted_solutions = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
        best_task_type = sorted_solutions[0][0]

        logger.info(f"检索到最相关解决方案: {best_task_type} (相似度: {sorted_solutions[0][1]:.3f})")

        return self.solutions[best_task_type]

    def _keyword_based_retrieval(self, user_query: str) -> Dict[str, Any]:
        """
        基于关键词的解决方案检索（备用方案）

        Args:
            user_query: 用户查询

        Returns:
            最相关的解决方案
        """
        # 定义关键词映射
        keyword_map = {
            "岸线类型识别": ["识别", "分类", "类型", "是什么岸线"],
            "岸线统计分析": ["多少", "统计", "长度", "占比", "百分比", "公里"],
            "岸线知识问答": ["什么是", "为什么", "如何", "原理", "定义", "概念"],
            "水体提取": ["提取", "边界", "水体", "影像"],
            "区域对比分析": ["对比", "比较", "哪个", "差异"]
        }

        # 计算关键词匹配分数
        scores = {}
        for task_type, keywords in keyword_map.items():
            score = sum(1 for kw in keywords if kw in user_query)
            scores[task_type] = score

        # 返回得分最高的解决方案
        best_task_type = max(scores, key=scores.get)

        # 如果所有得分都是0，返回默认的知识问答
        if scores[best_task_type] == 0:
            best_task_type = "岸线知识问答"

        logger.info(f"关键词匹配到解决方案: {best_task_type}")

        return self.solutions[best_task_type]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算余弦相似度

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            余弦相似度 (0-1)
        """
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def get_all_solutions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有解决方案"""
        return self.solutions

    def add_solution(self, task_type: str, solution: Dict[str, Any]):
        """
        添加新的解决方案

        Args:
            task_type: 任务类型
            solution: 解决方案字典
        """
        self.solutions[task_type] = solution

        # 重新构建嵌入向量
        if self.embedder:
            self._build_solution_embeddings()

        logger.info(f"已添加新解决方案: {task_type}")

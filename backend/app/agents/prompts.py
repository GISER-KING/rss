"""
层次化提示工程系统
基于RS-Agent论文的Hierarchical Prompt Engineering实现

提示层次：
1. 系统角色提示 (System Role)
2. 任务分类提示 (Task Classification)
3. 任务规划提示 (Task Planning)
4. 结果综合提示 (Result Synthesis)
"""


class HierarchicalPromptEngine:
    """层次化提示引擎"""

    # 第1层：系统角色提示
    SYSTEM_ROLE = """你是河流岸线空间智能分析专家，具备以下能力：

1. **岸线知识理解**：精通岸线分类、生态功能、保护政策等专业知识
2. **空间数据分析**：能够处理遥感影像、矢量数据、统计数据
3. **工具调用能力**：可以调用水体提取、岸线分类、统计分析等工具
4. **知识检索能力**：能够从学术文献和岸线数据库中检索相关信息

你的回答应该：
- 准确：基于科学文献和实际数据
- 专业：使用规范的学术术语
- 完整：提供充分的上下文和引用
- 实用：给出可操作的分析结果
"""

    # 第2层：任务分类提示
    TASK_CLASSIFICATION_PROMPT = """【任务分类阶段】

分析用户查询，判断属于以下哪种任务类型：

1. **岸线类型识别**：需要识别或分类岸线类型
   - 关键词：识别、分类、是什么类型
   - 示例："识别朝阳区的岸线类型"

2. **岸线统计分析**：需要计算数值、统计指标
   - 关键词：多少、长度、占比、统计
   - 示例："朝阳区有多少公里自然岸线"

3. **岸线知识问答**：需要解释概念、原理、方法
   - 关键词：什么是、为什么、如何、原理
   - 示例："什么是生态岸线"

4. **水体提取**：需要从影像中提取水体边界
   - 关键词：提取、边界、水体、影像
   - 示例："提取这张影像的水体"

5. **区域对比分析**：需要对比多个区域
   - 关键词：对比、比较、哪个、差异
   - 示例："对比朝阳区和海淀区的岸线"

用户查询：{query}

请判断任务类型并输出：
任务类型：[类型名称]
置信度：[0-1之间的数值]
"""

    # 第3层：任务规划提示
    TASK_PLANNING_PROMPT = """【任务规划阶段】

根据检索到的解决方案，制定详细的执行计划。

**任务类型**：{task_type}

**解决方案指导**：
{solution_guidance}

**用户查询**：{query}

**可用工具**：
{available_tools}

**知识库信息**：
- 文档流：{doc_count}篇学术文献
- 数据流：{data_count}条岸线数据

请制定执行计划，包括：
1. 需要调用的工具及参数
2. 需要检索的知识（文档流/数据流）
3. 执行步骤的先后顺序
4. 预期输出格式
"""

    # 第4层：结果综合提示
    RESULT_SYNTHESIS_PROMPT = """【结果综合阶段】

综合工具执行结果和知识检索结果，生成最终答案。

**用户查询**：{query}

**工具执行结果**：
{tool_results}

**知识检索结果**：
{knowledge_results}

请生成完整的回答，要求：
1. 直接回答用户问题
2. 提供具体的数据和证据
3. 引用相关文献或数据来源
4. 使用清晰的格式（表格、列表等）
5. 如有图表，使用Markdown语法展示
"""

    @classmethod
    def get_system_prompt(cls) -> str:
        """获取系统角色提示"""
        return cls.SYSTEM_ROLE

    @classmethod
    def get_task_classification_prompt(cls, query: str) -> str:
        """获取任务分类提示"""
        return cls.TASK_CLASSIFICATION_PROMPT.format(query=query)

    @classmethod
    def get_task_planning_prompt(
        cls,
        task_type: str,
        solution_guidance: str,
        query: str,
        available_tools: str,
        doc_count: int,
        data_count: int
    ) -> str:
        """获取任务规划提示"""
        return cls.TASK_PLANNING_PROMPT.format(
            task_type=task_type,
            solution_guidance=solution_guidance,
            query=query,
            available_tools=available_tools,
            doc_count=doc_count,
            data_count=data_count
        )

    @classmethod
    def get_result_synthesis_prompt(
        cls,
        query: str,
        tool_results: str,
        knowledge_results: str
    ) -> str:
        """获取结果综合提示"""
        return cls.RESULT_SYNTHESIS_PROMPT.format(
            query=query,
            tool_results=tool_results,
            knowledge_results=knowledge_results
        )

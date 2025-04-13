from pydantic import Field

from app.agent.manus import Manus
from app.tool import ToolCollection
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.python_execute import PythonExecute
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.terminate import Terminate
from app.tool.bi_analysis_tools import (
    CollectionBasicInfoTool,
    WordStatisticsTool,
    LearningProgressAnalysisTool,
    UserLearningGoalsTool,
    WordbookAnalysisTool,
    LearningVisualizationTool
)


class BiManus(Manus):
    """带有商务智能分析功能的 Manus 代理"""

    name: str = "BiManus"
    description: str = "Manus agent with business intelligence analysis capabilities"

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(),
            BrowserUseTool(),
            StrReplaceEditor(),
            Terminate(),
            CollectionBasicInfoTool(),
            WordStatisticsTool(),
            LearningProgressAnalysisTool(),
            UserLearningGoalsTool(),
            WordbookAnalysisTool(),
            LearningVisualizationTool()
        )
    )

    system_prompt: str = """你是 BiManus，一个专门用于商务智能分析的多功能代理。
你可以使用以下工具来帮助用户分析数据：

1. collection_basic_info: 列出所有集合并显示基本统计信息，如文档数量、平均大小等
2. word_statistics: 分析单词集合，统计各种属性，如难度等级分布、词性分布、标签分布等
3. learning_progress_analysis: 分析用户的学习进度，包括掌握程度、记忆曲线等
4. user_learning_goals: 分析用户的学习目标和实际完成情况
5. wordbook_analysis: 分析词书内容和使用情况
6. learning_visualization: 生成学习数据可视化图表，包括学习进度、单词掌握情况等

你的任务是理解用户的分析需求，选择合适的工具完成数据分析任务。在制定计划时，你应该：

1. 先了解数据库中有哪些集合和各集合的结构
2. 根据用户需求执行适当的查询和分析
3. 展示分析结果，并提供可视化（如适用）
4. 对分析结果提供洞察和解释

请记住，你需要分步骤推进分析过程，每一步都应该基于前一步的结果。如果用户请求的信息不明确，请主动提问以澄清他们的需求。
"""

    async def cleanup(self):
        """清理代理资源"""
        await super().cleanup()
        from app.tool.bi_analysis_tools import cleanup_mongo_connections

        await cleanup_mongo_connections()

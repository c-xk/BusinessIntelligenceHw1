import asyncio
import os
from dotenv import load_dotenv

from app.agent.bi_manus import BiManus
from app.agent.manus_enhanced import EnhancedManus
from app.logger import logger
from app.tool.bi_analysis_tools import (
    CollectionBasicInfoTool,
    WordStatisticsTool,
    LearningProgressAnalysisTool,
    UserLearningGoalsTool,
    WordbookAnalysisTool,
    LearningVisualizationTool
)
from app.tool import ToolCollection


class BiEnhancedManus(EnhancedManus):
    """
    增强版的BI分析Manus代理，结合了BiManus的功能和EnhancedManus的Next Plan功能
    """

    name: str = "BiEnhancedManus"
    description: str = "Enhanced BI Analysis Manus agent with Next Plan capabilities"

    def __init__(self, **data):
        super().__init__(**data)

        # 初始化BI分析工具
        self.available_tools = ToolCollection(
            CollectionBasicInfoTool(),
            WordStatisticsTool(),
            LearningProgressAnalysisTool(),
            UserLearningGoalsTool(),
            WordbookAnalysisTool(),
            LearningVisualizationTool()
        )

        # 设置系统提示
        self.system_prompt = """你是 BiEnhancedManus，一个专门用于商务智能分析的增强多功能代理。
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


async def main():
    """主函数"""
    # 加载环境变量
    load_dotenv()

    # 创建代理实例
    agent = BiEnhancedManus()

    try:
        # 欢迎信息
        print("=" * 50)
        print("欢迎使用BiEnhancedManus - AI驱动的BI分析助手")
        print("=" * 50)
        print("您可以查询单词学习数据、用户学习进度、词书内容等信息")
        print("示例查询:")
        print("1. 分析所有德语单词的难度和词性分布")
        print("2. 查看用户'user123'的学习进度和目标完成情况")
        print("3. 分析'A1'标签的单词特征")
        print("4. 生成用户学习活动的可视化图表")
        print("=" * 50)

        # 获取用户输入
        prompt = input("请输入您的分析需求: ")

        if not prompt.strip():
            logger.warning("输入为空，无法处理。")
            return

        # 执行分析
        logger.info("正在处理分析请求...")
        print("\n开始分析...\n")

        await agent.run(prompt)

        logger.info("分析请求处理完成。")

    except KeyboardInterrupt:
        logger.warning("操作被中断。")
        print("\n操作已取消。")

    except Exception as e:
        logger.error(f"执行过程中发生错误: {str(e)}")
        print(f"\n执行过程中发生错误: {str(e)}")

    finally:
        # 确保在退出前清理资源
        print("\n清理资源...")
        from app.tool.bi_analysis_tools import cleanup_mongo_connections
        await cleanup_mongo_connections()
        await agent.cleanup()
        print("已退出。")


if __name__ == "__main__":
    # 在Windows上可能需要使用不同的事件循环策略
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())

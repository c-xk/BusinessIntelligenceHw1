import json
import re
from typing import Any, Dict, List, Optional, Union, Tuple
import asyncio

from pydantic import BaseModel, Field

from app.agent.base import BaseAgent
from app.exceptions import ToolError, OpenManusError
from app.logger import logger
from app.schema import Message
from app.tool import ToolCollection
from app.tool.base import ToolResult


# 自定义异常，替代原始的ExecutionError
class ExecutionError(OpenManusError):
    """Exception raised when execution fails"""
    pass


class ExecutionStep(BaseModel):
    """单个执行步骤的信息"""
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Optional[ToolResult] = None
    error: Optional[str] = None


class NextPlan(BaseModel):
    """下一步计划"""
    reasoning: Optional[str] = None
    next_steps: List[Dict[str, Any]] = Field(default_factory=list)


class EnhancedManus(BaseAgent):
    """
    增强版的Manus代理，包含Next Plan功能
    """

    name: str = "EnhancedManus"
    description: str = "Enhanced Manus agent with Next Plan capabilities"

    available_tools: ToolCollection = Field(default_factory=ToolCollection)
    system_prompt: str = """你是一个智能代理，能够帮助用户完成复杂任务。
你可以使用一系列工具来完成任务，根据用户需求规划执行步骤。
请谨慎分析任务，选择合适的工具，并按照逻辑顺序执行。"""

    def __init__(self, **data: Any):
        super().__init__(**data)
        # 初始化执行历史记录
        self.execution_history: List[ExecutionStep] = []
        # 初始化用户查询
        self.user_query: str = ""
        # 指定最大执行步骤数，防止无限循环
        self.max_execution_steps: int = 15

    def _get_system_prompt(self) -> str:
        """获取系统提示信息"""
        # 直接返回设置的系统提示，而不是从外部导入
        return self.system_prompt

    async def step(self, input_message: str) -> str:
        """
        执行一个步骤，实现BaseAgent的抽象方法

        Args:
            input_message: 输入消息

        Returns:
            str: 输出消息
        """
        # 保存用户查询
        self.user_query = input_message

        # 直接执行第一个工具
        try:
            # 分析并解析用户请求
            language = None
            tag = None

            # 提取语言信息
            if "德语" in input_message:
                language = "de"
            elif "英语" in input_message:
                language = "en"

            # 提取标签信息
            a1_match = re.search(r'A1', input_message, re.IGNORECASE)
            a2_match = re.search(r'A2', input_message, re.IGNORECASE)
            b1_match = re.search(r'B1', input_message, re.IGNORECASE)
            b2_match = re.search(r'B2', input_message, re.IGNORECASE)
            c1_match = re.search(r'C1', input_message, re.IGNORECASE)

            if a1_match:
                tag = "A1"
            elif a2_match:
                tag = "A2"
            elif b1_match:
                tag = "B1"
            elif b2_match:
                tag = "B2"
            elif c1_match:
                tag = "C1"

            # 提取其他可能的标签
            tag_matches = re.findall(r'标签[：:]\s*([^\s,，]+)', input_message)
            if tag_matches:
                tag = tag_matches[0]

            # 设置查询参数
            query_params = {}
            if language:
                query_params["language"] = language
            if tag:
                query_params["tag"] = tag

            # 如果是分析单词请求
            if ("单词" in input_message or "词汇" in input_message) and ("分析" in input_message or "统计" in input_message):
                print(f"正在分析单词数据... 参数: {query_params}")
                result = await self.available_tools.execute(
                    name="word_statistics",
                    tool_input=query_params
                )
                if result:
                    return f"单词分析结果:\n{result.output}"
                else:
                    return "无法分析单词数据。请确保数据库中有相关单词数据。"

            # 获取数据库基本信息
            print("正在获取数据库基本信息...")
            result = await self.available_tools.execute(
                name="collection_basic_info",
                tool_input={}
            )
            if result:
                return f"数据库信息:\n{result.output}"
            else:
                return "无法获取数据库信息。请检查数据库连接。"

        except Exception as e:
            error_message = f"执行过程中出错: {str(e)}"
            logger.error(error_message)
            return error_message

    async def get_initial_plan(self, prompt: str) -> List[Dict[str, Any]]:
        """
        获取初始计划 - 根据提示词创建匹配用户需求的计划

        Args:
            prompt: 用户输入的提示

        Returns:
            List[Dict[str, Any]]: 初始计划
        """
        # 分析并解析用户请求
        language = None
        tag = None

        # 提取语言信息
        if "德语" in prompt:
            language = "de"
        elif "英语" in prompt:
            language = "en"

        # 提取标签信息
        a1_match = re.search(r'A1', prompt, re.IGNORECASE)
        a2_match = re.search(r'A2', prompt, re.IGNORECASE)
        b1_match = re.search(r'B1', prompt, re.IGNORECASE)
        b2_match = re.search(r'B2', prompt, re.IGNORECASE)
        c1_match = re.search(r'C1', prompt, re.IGNORECASE)

        if a1_match:
            tag = "A1"
        elif a2_match:
            tag = "A2"
        elif b1_match:
            tag = "B1"
        elif b2_match:
            tag = "B2"
        elif c1_match:
            tag = "C1"

        # 提取其他可能的标签
        if "名词" in prompt:
            tag = "名词"
        elif "动词" in prompt:
            tag = "动词"
        elif "形容词" in prompt:
            tag = "形容词"
        elif "家具" in prompt:
            tag = "家具"
        elif "建筑" in prompt:
            tag = "建筑"

        # 设置查询参数
        query_params = {}
        if language:
            query_params["language"] = language
        if tag:
            query_params["tag"] = tag

        # 规则匹配来生成计划
        if ("单词" in prompt or "词汇" in prompt) and ("分析" in prompt or "统计" in prompt):
            # 先获取基础信息，再进行详细分析
            return [
                {
                    "tool_name": "collection_basic_info",
                    "tool_input": {}
                }
            ]
        elif "学习进度" in prompt:
            return [
                {
                    "tool_name": "learning_progress_analysis",
                    "tool_input": {"user_id": "ed62add4-bf40-4246-b7ab-2555015b383b"}
                }
            ]
        elif "词书" in prompt:
            return [
                {
                    "tool_name": "wordbook_analysis",
                    "tool_input": {"wordbook_id": "67b476007f33104e40786b99"}
                }
            ]
        elif "可视化" in prompt or "图表" in prompt:
            return [
                {
                    "tool_name": "learning_visualization",
                    "tool_input": {
                        "user_id": "ed62add4-bf40-4246-b7ab-2555015b383b",
                        "chart_type": "progress_trend"
                    }
                }
            ]
        else:
            # 默认返回基本信息查询
            return [
                {
                    "tool_name": "collection_basic_info",
                    "tool_input": {}
                }
            ]

    async def get_next_plan(self) -> NextPlan:
        """
        获取下一步执行计划 - 根据历史和用户查询生成

        Returns:
            NextPlan: 下一步执行计划
        """
        # 如果历史记录为空，返回空计划
        if not self.execution_history:
            return NextPlan(
                reasoning="没有执行历史，无法生成下一步计划",
                next_steps=[]
            )

        # 获取最后一个执行步骤
        last_step = self.execution_history[-1]

        # 分析用户查询，提取语言和标签信息
        language = None
        tag = None

        # 提取语言信息
        if "德语" in self.user_query:
            language = "de"
        elif "英语" in self.user_query:
            language = "en"

        # 提取标签信息
        a1_match = re.search(r'A1', self.user_query, re.IGNORECASE)
        a2_match = re.search(r'A2', self.user_query, re.IGNORECASE)
        b1_match = re.search(r'B1', self.user_query, re.IGNORECASE)
        b2_match = re.search(r'B2', self.user_query, re.IGNORECASE)
        c1_match = re.search(r'C1', self.user_query, re.IGNORECASE)

        if a1_match:
            tag = "A1"
        elif a2_match:
            tag = "A2"
        elif b1_match:
            tag = "B1"
        elif b2_match:
            tag = "B2"
        elif c1_match:
            tag = "C1"

        # 提取其他可能的标签
        if "名词" in self.user_query:
            tag = "名词"
        elif "动词" in self.user_query:
            tag = "动词"
        elif "形容词" in self.user_query:
            tag = "形容词"
        elif "家具" in self.user_query:
            tag = "家具"
        elif "建筑" in self.user_query:
            tag = "建筑"

        # 设置查询参数
        query_params = {}
        if language:
            query_params["language"] = language
        if tag:
            query_params["tag"] = tag

        # 如果是collection_basic_info，接下来针对单词执行word_statistics
        if last_step.tool_name == "collection_basic_info" and ("单词" in self.user_query or "词汇" in self.user_query):
            return NextPlan(
                reasoning="已获取数据库基本信息，接下来分析单词数据",
                next_steps=[
                    {
                        "tool_name": "word_statistics",
                        "tool_input": query_params
                    }
                ]
            )

        # 结束执行
        return NextPlan(
            reasoning="已完成所有必要的分析，执行完成",
            next_steps=[]
        )

    async def execute_step(self, step: Dict[str, Any]) -> Tuple[bool, Optional[ToolResult], Optional[str]]:
        """
        执行单个步骤

        Args:
            step: 步骤信息

        Returns:
            Tuple[bool, Optional[ToolResult], Optional[str]]: 执行结果，包括是否成功、输出和错误信息
        """
        tool_name = step.get("tool_name")
        tool_input = step.get("tool_input", {})

        if not tool_name:
            logger.error("步骤中缺少工具名称")
            return False, None, "步骤中缺少工具名称"

        try:
            # 查找并执行工具
            result = await self.available_tools.execute(name=tool_name, tool_input=tool_input)
            return True, result, None
        except ToolError as e:
            error_message = f"工具执行错误: {str(e)}"
            logger.error(error_message)
            return False, None, error_message
        except Exception as e:
            error_message = f"执行步骤时发生未知错误: {str(e)}"
            logger.error(error_message)
            return False, None, error_message

    async def run_with_next_plan(self, prompt: str) -> None:
        """
        使用Next Plan功能运行代理

        Args:
            prompt: 用户查询
        """
        # 保存用户查询
        self.user_query = prompt
        logger.info(f"用户查询: {prompt}")

        # 初始化执行历史
        self.execution_history = []

        # 获取初始计划
        initial_plan = await self.get_initial_plan(prompt)

        if not initial_plan:
            logger.warning("未能获取有效的初始计划")
            print("我无法为您的请求生成执行计划。请尝试更明确地描述您的需求。")
            return

        # 执行初始计划的第一步
        if initial_plan:
            first_step = initial_plan[0]
            print(f"执行步骤 1: 使用工具 {first_step.get('tool_name')}")
            success, result, error = await self.execute_step(first_step)

            # 记录执行结果
            step_record = ExecutionStep(
                tool_name=first_step.get("tool_name", "unknown"),
                tool_input=first_step.get("tool_input", {})
            )

            if success and result:
                step_record.tool_output = result
                print(f"执行工具 {first_step.get('tool_name')} 的结果:\n{result.output}")
            else:
                step_record.error = error
                print(f"执行工具 {first_step.get('tool_name')} 时出错:\n{error}")

            self.execution_history.append(step_record)

        # 循环执行Next Plan
        step_count = 1
        while step_count < self.max_execution_steps:
            # 获取下一步计划
            next_plan = await self.get_next_plan()

            # 如果没有下一步，或者下一步是终止命令，则结束执行
            if not next_plan.next_steps:
                logger.info("没有更多步骤，执行完成")
                print("\n任务执行完成。")
                break

            # 输出推理过程
            if next_plan.reasoning:
                print(f"\n思考过程:\n{next_plan.reasoning}\n")

            # 执行下一步
            for step in next_plan.next_steps:
                step_count += 1

                # 检查是否是终止命令
                if step.get("tool_name") == "terminate":
                    reason = step.get("tool_input", {}).get("reason", "任务已完成")
                    print(f"\n终止执行: {reason}")
                    return

                # 执行步骤
                print(f"\n执行步骤 {step_count}: 使用工具 {step.get('tool_name')}")
                success, result, error = await self.execute_step(step)

                # 记录执行结果
                step_record = ExecutionStep(
                    tool_name=step.get("tool_name", "unknown"),
                    tool_input=step.get("tool_input", {})
                )

                if success and result:
                    step_record.tool_output = result
                    print(f"执行结果:\n{result.output}")
                else:
                    step_record.error = error
                    print(f"执行出错:\n{error}")

                self.execution_history.append(step_record)

                # 如果是单步执行，每次只执行一个步骤然后重新评估
                break

            # 如果达到最大步骤数，中断执行
            if step_count >= self.max_execution_steps:
                print(f"\n已达到最大执行步骤数 ({self.max_execution_steps})，执行终止。")
                break

        logger.info(f"总共执行了 {step_count} 个步骤")

    async def run(self, prompt: str) -> None:
        """
        运行代理

        Args:
            prompt: 用户查询
        """
        await self.run_with_next_plan(prompt)

    async def cleanup(self):
        """清理资源"""
        pass

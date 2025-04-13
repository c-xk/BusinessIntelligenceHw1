from pydantic import Field

from app.agent.manus import Manus
from app.tool import ToolCollection
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.python_execute import PythonExecute
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.terminate import Terminate
from app.tool.word_dict_tools import WordByTagTool, WordDetailTool, WordSynAntTool


class DictionaryManus(Manus):
    """带有德语词典功能的 Manus 代理"""

    name: str = "DictionaryManus"
    description: str = "Manus agent with German dictionary capabilities"

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(),
            BrowserUseTool(),
            StrReplaceEditor(),
            Terminate(),
            WordDetailTool(),
            WordByTagTool(),
            WordSynAntTool(),
        )
    )

    system_prompt: str = """你是 DictionaryManus，一个具有德语词典功能的多功能代理。
你可以使用以下工具来帮助用户学习德语：

1. word_detail: 查询单词的详细信息，包括定义、发音、词性等
2. query_by_tag: 根据标签查询所有单词，例如 A2、名词、建筑等
3. syn_ant_query: 查询单词的同义词和反义词

当用户需要查询德语单词时，请优先使用这些专门的词典工具。
"""

    async def cleanup(self):
        """清理代理资源"""
        await super().cleanup()
        from app.tool.word_dict_tools import cleanup_mongo_connections

        await cleanup_mongo_connections()

import os
from typing import Any, Dict

from dotenv import load_dotenv
from pymongo import MongoClient

from app.exceptions import ToolError
from app.tool.base import BaseTool, ToolResult

load_dotenv()
host = os.getenv("HOST")
port = os.getenv("PORT")
database = os.getenv("DATABASE")
username = os.getenv("USER_NAME")
password = os.getenv("PASSWORD")
auth_db = os.getenv("AUTH_DB")
print(host, port, database, username, password, auth_db)


def get_mongo_collection():

    uri = (
        f"mongodb://{username}:{password}@{host}:{port}/{database}?authSource={auth_db}"
    )
    client = MongoClient(uri)
    db = client[database]
    collection = db["words"]
    return collection


class WordDetailTool(BaseTool):
    name: str = "word_detail"
    description: str = "查询单词的详细信息，包括定义、发音、词性等"

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "word": {
                "type": "string",
                "description": "需要查询的德语单词，例如 'der Keller'",
            }
        },
        "required": ["word"],
    }

    async def execute(self, **kwargs) -> ToolResult:
        word = kwargs.get("word", "")
        try:
            coll = get_mongo_collection()
            doc = coll.find_one({"word": word})
            if not doc:
                return ToolResult(output=f"未找到单词：{word}")

            pos_info = doc["partOfSpeechList"][0]
            definitions = ", ".join(pos_info.get("definitions", []))
            ipa = doc["phonetics"][0].get("ipa", "") if doc.get("phonetics") else "无"
            gender = pos_info.get("gender", "")
            part = pos_info.get("type", "")
            plural = pos_info.get("plural", "")

            result = f"""单词：{word}
性别：{gender}
词性：{part}
释义：{definitions}
复数：{plural}
音标：{ipa}"""

            return ToolResult(output=result)
        except Exception as e:
            raise ToolError(str(e))


class WordByTagTool(BaseTool):
    name: str = "query_by_tag"
    description: str = "根据标签查询所有单词，例如 A2、名词、建筑等"

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {"tag": {"type": "string", "description": "标签名，例如 '建筑'"}},
        "required": ["tag"],
    }

    async def execute(self, **kwargs) -> ToolResult:
        tag = kwargs.get("tag", "")
        try:
            coll = get_mongo_collection()
            cursor = coll.find({"tags": tag}, {"word": 1})
            words = [doc["word"] for doc in cursor]

            if not words:
                return ToolResult(output=f"没有找到标签为 '{tag}' 的单词")

            return ToolResult(
                output=f"标签为 '{tag}' 的单词包括：\n" + ", ".join(words)
            )
        except Exception as e:
            raise ToolError(str(e))


class WordSynAntTool(BaseTool):
    name: str = "syn_ant_query"
    description: str = "查询单词的同义词和反义词"

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {"word": {"type": "string", "description": "要查询的单词"}},
        "required": ["word"],
    }

    async def execute(self, **kwargs) -> ToolResult:
        word = kwargs.get("word", "")
        try:
            coll = get_mongo_collection()
            doc = coll.find_one({"word": word})

            if not doc:
                return ToolResult(output=f"未找到单词：{word}")

            synonyms = ", ".join(doc.get("synonyms", [])) or "无"
            antonyms = ", ".join(doc.get("antonyms", [])) or "无"

            return ToolResult(
                output=f"单词：{word}\n同义词：{synonyms}\n反义词：{antonyms}"
            )
        except Exception as e:
            raise ToolError(str(e))


async def cleanup_mongo_connections():
    pass


from app.tool import ToolCollection


class DictionaryTools:
    """德语词典工具集合"""

    @staticmethod
    def get_tools() -> ToolCollection:
        """获取所有词典工具"""
        return ToolCollection(WordDetailTool(), WordByTagTool(), WordSynAntTool())

    @staticmethod
    async def cleanup():
        """清理资源"""
        await cleanup_mongo_connections()

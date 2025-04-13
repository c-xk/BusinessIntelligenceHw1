# app/tools/say_hello_tool.py
from app.tool.base import BaseTool
from pydantic import Field

class SayHelloTool(BaseTool):
    name: str = Field(default="say_hello", description="打招呼工具")
    description: str = "一个简单的工具，可以向用户打招呼"

    async def execute(self, input_text: str) -> str:
        return f"{input_text}！我是 SayHelloTool，很高兴认识你～"

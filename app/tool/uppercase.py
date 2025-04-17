from app.tool.base import BaseTool

class UppercaseConverter(BaseTool):
    name: str = "UppercaseConverter"
    description: str = "将一个名为 input_text 的参数转换为大写形式。例如：input_text='hello'，返回 'HELLO'。"

    async def  execute(self, **kwargs) -> str:
        input_text = kwargs.get("input_text", "")
        return input_text.upper()

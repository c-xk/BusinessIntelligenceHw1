from app.tool.say_hello_tool import SayHelloTool
from app.agent.base import BaseAgent
from app.tool import ToolCollection

class HelloManus(BaseAgent):
    """一个简单的包含 SayHelloTool 的代理"""

    name: str = "HelloManus"
    description: str = "Manus agent that greets users with a hello message"

    available_tools: ToolCollection = ToolCollection(
        SayHelloTool()  # 注册 SayHelloTool
    )

    async def run(self, prompt: str) -> str:
        """处理传入的 prompt，执行工具"""
        tool = self.available_tools.get_tool('say_hello')  # 获取 'say_hello' 工具
        if tool:
            return await tool.execute(input_text=prompt)  # 调用 execute 方法
        else:
            return "没有找到可以处理请求的工具"

    async def step(self):
        """实现 step 方法"""
        return "HelloManus 代理运行中..."  # 返回一个简单的字符串作为示例

    async def cleanup(self):
        """清理代理资源"""
        # 在这里可以添加清理代码，释放资源等
        print("HelloManus 清理完毕！")

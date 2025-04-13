import asyncio
from app.agent.hello_manus import HelloManus  # 导入自定义代理类
from app.logger import logger

async def main():
    agent = HelloManus()  # 直接创建代理实例

    try:
        prompt = input("Enter your prompt: ")
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return

        logger.warning("Processing your request...")
        result = await agent.run(prompt)  # 执行代理的 run 方法
        print(result)  # 输出结果
        logger.info("Request processing completed.")
    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")
    finally:
        await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(main())

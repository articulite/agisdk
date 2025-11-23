import asyncio
from dotenv import load_dotenv

load_dotenv()

from agi_agents.qwen.qwen import QwenAgent
from arena import RunHarness


async def main():
    agent = QwenAgent()

    harness = RunHarness(
        agent=agent,
        tasks=[
            "gocalendar-1.json" # was "src/benchmarks/hackathon/tasks/*"
            #"src/benchmarks/hackathon/tasks/*"
        ],
        parallel=1, # was 60
        sample_count=1,
        max_steps=60,
        headless=True
    )

    results = await harness.run()
    print(results)


if __name__ == "__main__":
    asyncio.run(main())

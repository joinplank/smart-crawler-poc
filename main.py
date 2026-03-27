"""
Smart Crawler POC — Entry Point

A minimal web crawler agent that uses Gemini to drive a browser
through an observe → act → evaluate → finish loop.
"""

import asyncio
from pathlib import Path
from dotenv import load_dotenv
from gemini_provider import Gemini
from agent import Agent

load_dotenv()

INPUT_FILE = Path("input.md")


async def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"{INPUT_FILE} not found. Add your task there and re-run.")

    task = INPUT_FILE.read_text().strip()
    if not task:
        raise ValueError(f"{INPUT_FILE} is empty. Add a task description and re-run.")

    print(f"🤖 Task: {task}")
    print(f"\n🚀 Starting agent...\n")

    gemini = Gemini(model="gemini-2.5-flash")
    agent = Agent(gemini=gemini, headless=False, max_steps=15)

    result = await agent.run(task)
    print(f"\n📋 Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())

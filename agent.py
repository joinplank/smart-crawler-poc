"""
Smart Crawler Agent — observe → act → evaluate → finish/retry loop.

Uses Playwright for browser control and Gemini for decision-making.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Page
from gemini_provider import Gemini
from tools import TOOLS, TOOL_DEFINITIONS


# ---------------------------------------------------------------------------
# Browser state extraction (the "observe" step)
# ---------------------------------------------------------------------------

EXTRACT_STATE_JS = """
() => {
    let idx = 0;
    const interactives = [];
    const selectors = 'a, button, input, textarea, select, [role="button"], [role="link"], [onclick]';

    for (const el of document.querySelectorAll(selectors)) {
        if (el.offsetParent === null) continue;           // skip hidden elements
        el.setAttribute('data-agent-index', idx);
        const tag = el.tagName.toLowerCase();
        const type = el.getAttribute('type') || '';
        const text = (el.textContent || '').trim().slice(0, 80);
        const placeholder = el.getAttribute('placeholder') || '';
        const value = el.value || '';
        const label = tag === 'input' || tag === 'textarea' || tag === 'select'
            ? `[${idx}] <${tag}> type="${type}" placeholder="${placeholder}" value="${value}"`
            : `[${idx}] <${tag}> "${text}"`;
        interactives.push(label);
        idx++;
    }
    return interactives;
}
"""


async def get_browser_state(page: Page) -> str:
    """Extract current page state as a text description for the LLM."""
    url = page.url
    title = await page.title()
    try:
        elements = await page.evaluate(EXTRACT_STATE_JS)
    except Exception:
        elements = []

    elements_text = "\n".join(elements) if elements else "(no interactive elements found)"

    return (
        f"## Browser State\n\n"
        f"**URL:** {url}\n"
        f"**Title:** {title}\n\n"
        f"**Interactive Elements:**\n{elements_text}"
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class Agent:
    def __init__(self, gemini: Gemini, headless: bool = False, max_steps: int = 15):
        self.gemini = gemini
        self.headless = headless
        self.max_steps = max_steps

    async def run(self, task: str) -> str:
        system_prompt = Path("prompts/agent.md").read_text()

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            await page.goto("about:blank")

            messages: list[dict] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"TASK: {task}"},
            ]

            tool_result = "No previous action."

            for step in range(1, self.max_steps + 1):
                # ── Observe ──────────────────────────────────────
                state = await get_browser_state(page)
                state_msg = f"{state}\n\n**Previous tool result:** {tool_result}\n\n**Step:** {step}/{self.max_steps}"
                messages.append({"role": "user", "content": state_msg})

                # ── Think + Act (LLM decides which tool to call) ─
                response = await self.gemini.call(messages, TOOL_DEFINITIONS)

                # Remove the state message to keep history lean
                messages.pop()

                if response["type"] == "text":
                    # LLM didn't call a tool — nudge it
                    print(f"  ⚠ Step {step}: LLM returned text instead of a tool call, retrying...")
                    messages.append({"role": "user", "content": "You must call a tool. Use done_tool if the task is complete."})
                    continue

                tool_name = response["name"]
                tool_args = response["args"]
                thought = tool_args.pop("thought", "")

                print(f"  💭 Step {step}: {thought}")
                print(f"  🔧 {tool_name}({', '.join(f'{k}={v!r}' for k, v in tool_args.items())})")

                # ── Execute the tool ─────────────────────────────
                tool_fn = TOOLS.get(tool_name)
                if not tool_fn:
                    tool_result = f"Unknown tool: {tool_name}"
                    print(f"  ❌ {tool_result}")
                    continue

                try:
                    tool_result = await tool_fn(page, **tool_args)
                    print(f"  ✅ {tool_result}")
                except Exception as e:
                    tool_result = f"Tool error: {e}"
                    print(f"  ❌ {tool_result}")

                # Record the tool call + result in history
                messages.append({
                    "role": "model",
                    "tool_call": {"name": tool_name, "args": tool_args},
                    "tool_response": tool_result,
                })

                # ── Evaluate ─────────────────────────────────────
                if tool_name == "done_tool":
                    print(f"\n🏁 Agent finished: {tool_result}")
                    await browser.close()
                    return tool_result

            print(f"\n⏱ Agent reached max steps ({self.max_steps}) without completing.")
            await browser.close()
            return "Max steps reached without completing the task."

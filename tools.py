"""
Browser tools for the smart crawler agent.

Each tool is a simple async function that takes a Playwright page and returns a string result.
Tool definitions are plain dicts for Gemini's function calling API.
"""

# ---------------------------------------------------------------------------
# Tool definitions (JSON schemas for Gemini function calling)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "goto_tool",
        "description": "Navigate the browser to a URL. Always include the full protocol (https://).",
        "parameters": {
            "type": "object",
            "properties": {
                "thought": {"type": "string", "description": "Your reasoning for this action."},
                "url":     {"type": "string", "description": "The URL to navigate to."},
            },
            "required": ["thought", "url"],
        },
    },
    {
        "name": "click_tool",
        "description": "Click an interactive element on the page by its index label.",
        "parameters": {
            "type": "object",
            "properties": {
                "thought": {"type": "string", "description": "Your reasoning for this action."},
                "index":   {"type": "integer", "description": "Index label of the element to click."},
            },
            "required": ["thought", "index"],
        },
    },
    {
        "name": "type_tool",
        "description": "Type text into an input element by its index label.",
        "parameters": {
            "type": "object",
            "properties": {
                "thought":     {"type": "string",  "description": "Your reasoning for this action."},
                "index":       {"type": "integer", "description": "Index label of the input element."},
                "text":        {"type": "string",  "description": "The text to type."},
                "clear":       {"type": "boolean", "description": "Clear existing text before typing.", "default": False},
                "press_enter": {"type": "boolean", "description": "Press Enter after typing.", "default": False},
            },
            "required": ["thought", "index", "text"],
        },
    },
    {
        "name": "wait_tool",
        "description": "Pause execution for a given number of milliseconds. Use this to wait for animations, redirects, or delayed page loads.",
        "parameters": {
            "type": "object",
            "properties": {
                "thought":      {"type": "string",  "description": "Your reasoning for waiting."},
                "milliseconds": {"type": "integer", "description": "How many milliseconds to wait."},
            },
            "required": ["thought", "milliseconds"],
        },
    },
    {
        "name": "scrape_tool",
        "description": "Scrape all visible text from the current page and save it to a .txt file inside the results/ folder.",
        "parameters": {
            "type": "object",
            "properties": {
                "thought":   {"type": "string", "description": "Your reasoning for scraping."},
                "filename":  {"type": "string", "description": "Name of the output file (without extension), e.g. 'homepage'."},
            },
            "required": ["thought", "filename"],
        },
    },
    {
        "name": "done_tool",
        "description": "Signal that the task is complete (or impossible). Provide a summary of what was accomplished.",
        "parameters": {
            "type": "object",
            "properties": {
                "thought": {"type": "string", "description": "Your reasoning for completing the task."},
                "reason":  {"type": "string", "description": "Summary of what was accomplished or why the task failed."},
            },
            "required": ["thought", "reason"],
        },
    },
]

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def goto_tool(page, url: str, **_) -> str:
    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
    return f"Navigated to {url}"


async def click_tool(page, index: int, **_) -> str:
    element = page.locator(f"[data-agent-index='{index}']")
    await element.scroll_into_view_if_needed(timeout=3000)
    await element.click(timeout=5000)
    await page.wait_for_timeout(1000)  # brief pause for page reactions
    return f"Clicked element at index {index}"


async def type_tool(page, index: int, text: str, clear: bool = False, press_enter: bool = False, **_) -> str:
    element = page.locator(f"[data-agent-index='{index}']")
    await element.scroll_into_view_if_needed(timeout=3000)
    await element.click(timeout=3000)
    if clear:
        await element.fill("")
    await element.type(text, delay=50)
    if press_enter:
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(2000)
    return f"Typed '{text}' into element at index {index}"


async def wait_tool(page, milliseconds: int, **_) -> str:
    await page.wait_for_timeout(milliseconds)
    return f"Waited {milliseconds} ms"


async def scrape_tool(page, filename: str, **_) -> str:
    import re
    from pathlib import Path
    from datetime import datetime

    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    # Strip the filename of any directory components for safety
    safe_name = Path(filename).name
    if not safe_name:
        safe_name = "scrape"

    text = await page.evaluate("() => document.body.innerText")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = results_dir / f"{safe_name}_{timestamp}.txt"
    out_path.write_text(text, encoding="utf-8")

    return f"Scraped {len(text)} characters → {out_path}"


async def done_tool(page, reason: str, **_) -> str:
    return reason


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS = {
    "goto_tool":   goto_tool,
    "click_tool":  click_tool,
    "type_tool":   type_tool,
    "wait_tool":   wait_tool,
    "scrape_tool": scrape_tool,
    "done_tool":   done_tool,
}

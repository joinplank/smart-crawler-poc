# Smart Crawler POC

A minimal proof-of-concept showing how an LLM can autonomously control a browser through a simple agent loop.

## How it works

The agent follows a tight loop on every step:

```
Observe → Act → Evaluate → (repeat or finish)
```

1. **Observe** — reads the current page (URL, title, interactive elements labeled with index numbers)
2. **Act** — sends the state to Gemini, which picks a tool to call (`goto`, `click`, `type`, or `done`)
3. **Evaluate** — checks the result; if `done_tool` was called, finish; otherwise loop

## Tools

| Tool | Description |
|------|-------------|
| `goto_tool` | Navigate to a URL |
| `click_tool` | Click an element by its index |
| `type_tool` | Type text into an input by its index |
| `done_tool` | Signal task completion |

## Setup

```bash
cp .env.example .env        # add your GEMINI_API_KEY
pip3 install -r requirements.txt
python3 -m playwright install chromium
```

## Run

```bash
python3 main.py
```

**Example task:**
```
Go to https://practicetestautomation.com/practice-test-login/ and login with username 'student' and password 'Password123'
```

## File structure

```
main.py          # entry point
agent.py         # agent loop + browser state extraction
provider.py      # Gemini function-calling wrapper
tools.py         # browser tools + JSON schemas
prompts/
  system.md      # system prompt
```

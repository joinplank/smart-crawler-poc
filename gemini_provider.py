"""
Minimal Gemini provider for function calling.

Wraps the google-genai SDK to:
1. Convert our simple message format to Gemini's Content format
2. Send messages + tool definitions to the model
3. Return either a tool call (name + args) or a text response
"""

import os
from google import genai
from google.genai import types


class Gemini:
    def __init__(self, model: str = "gemini-2.5-flash", api_key: str | None = None):
        self.model = model
        self.client = genai.Client(
            api_key=api_key or os.environ.get("GEMINI_API_KEY")
        )

    async def call(self, messages: list[dict], tool_definitions: list[dict]) -> dict:
        """
        Send messages to Gemini and get back either a tool call or text.

        Args:
            messages: list of {"role": "system"|"user"|"model", "content": str}
                      or {"role": "model", "tool_call": {...}, "tool_response": str}
            tool_definitions: list of function declaration dicts

        Returns:
            {"type": "tool_call", "name": str, "args": dict}  or
            {"type": "text", "content": str}
        """
        system_instruction, contents = self._build_contents(messages)

        tools = [types.Tool(function_declarations=[
            types.FunctionDeclaration(
                name=td["name"],
                description=td["description"],
                parameters_json_schema=td["parameters"],
            )
            for td in tool_definitions
        ])]

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=tools,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        # Check for function call
        if response.function_calls:
            fc = response.function_calls[0]
            return {
                "type": "tool_call",
                "name": fc.name,
                "args": dict(fc.args) if fc.args else {},
            }

        # Otherwise return text
        text = response.text or ""
        return {"type": "text", "content": text}

    @staticmethod
    def _build_contents(messages: list[dict]) -> tuple[str | None, list[types.Content]]:
        """Convert our message list to Gemini's (system_instruction, contents) format."""
        system_instruction = None
        raw: list[types.Content] = []

        for msg in messages:
            role = msg["role"]

            if role == "system":
                system_instruction = msg["content"]

            elif role == "user":
                raw.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=msg["content"])],
                ))

            elif role == "model":
                # A model message that made a tool call
                if "tool_call" in msg:
                    tc = msg["tool_call"]
                    # Model's function call turn
                    raw.append(types.Content(
                        role="model",
                        parts=[types.Part.from_function_call(name=tc["name"], args=tc["args"])],
                    ))
                    # The function response (user turn)
                    raw.append(types.Content(
                        role="user",
                        parts=[types.Part.from_function_response(
                            name=tc["name"],
                            response={"result": msg.get("tool_response", "")},
                        )],
                    ))
                else:
                    raw.append(types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=msg.get("content", ""))],
                    ))

        # Merge consecutive same-role contents (Gemini requires strict alternation)
        merged: list[types.Content] = []
        for content in raw:
            if merged and content.role == merged[-1].role:
                merged[-1] = types.Content(
                    role=content.role,
                    parts=(merged[-1].parts or []) + (content.parts or []),
                )
            else:
                merged.append(content)

        return system_instruction, merged

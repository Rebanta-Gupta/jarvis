from groq import Groq
from config import GROQ_API_KEY
import json
import re

client = Groq(api_key=GROQ_API_KEY)


def _parse_failed_generation(error_str: str) -> dict | None:
    """
    When Groq returns tool_use_failed, the error contains the attempted
    function call. We parse it manually and execute it ourselves.
    Example: <function=add_note>{'content': 'buy groceries'}</function>
    """
    name_match = re.search(r"<function=(\w+)>", error_str)
    if not name_match:
        return None

    name = name_match.group(1)

    args_match = re.search(r"<function=\w+>(.+?)</function>", error_str, re.DOTALL)
    if not args_match:
        return None

    raw_args = args_match.group(1).strip()

    try:
        args = json.loads(raw_args)
    except json.JSONDecodeError:
        try:
            import ast
            args = ast.literal_eval(raw_args)
        except Exception:
            return None

    import uuid
    return {"id": f"call_{uuid.uuid4().hex[:8]}", "name": name, "args": args}


def chat(messages: list[dict], tools: list[dict] = None, system_prompt: str = "") -> dict:
    """
    Send a conversation to the LLM.
    Returns {"content": str, "tool_call": dict | None}

    system_prompt: pass the pre-built prompt from build_system_prompt()
                   so memory is injected per-turn.
    """
    kwargs = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            *messages,
        ],
        "max_tokens": 512,
        "temperature": 0.7,
    }

    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    try:
        response = client.chat.completions.create(**kwargs)
        message = response.choices[0].message

        if message.tool_calls:
            tool_call = message.tool_calls[0]
            return {
                "content": None,
                "tool_call": {
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "args": json.loads(tool_call.function.arguments),
                }
            }

        return {"content": message.content, "tool_call": None}

    except Exception as e:
        error = str(e)

        if "tool_use_failed" in error or "Failed to call a function" in error:
            parsed = _parse_failed_generation(error)
            if parsed:
                print(f"[debug] tool_use_failed — salvaging '{parsed['name']}' call")
                return {"content": None, "tool_call": parsed}

            print("[debug] tool_use_failed — could not parse, falling back to plain chat")
            kwargs.pop("tools", None)
            kwargs.pop("tool_choice", None)
            response = client.chat.completions.create(**kwargs)
            return {
                "content": response.choices[0].message.content,
                "tool_call": None
            }

        raise


def quick_extract(prompt: str, system_prompt: str = "") -> str:
    """
    Cheap single-turn call used by MemoryManager for fact extraction.
    No tools, low temperature for deterministic JSON output.
    """
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt or "You are a precise data extractor. Output only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=200,
        temperature=0.0,
    )
    return response.choices[0].message.content or "{}"
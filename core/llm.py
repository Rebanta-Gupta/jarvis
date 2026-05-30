import json
import re
import time
import uuid

from groq import Groq
from groq import RateLimitError, APIConnectionError, APIStatusError

from config import GROQ_API_KEY, LLM_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE

client = Groq(api_key=GROQ_API_KEY)

_RETRYABLE = (RateLimitError, APIConnectionError)
_MAX_RETRIES = 3


def _parse_failed_generation(error_str: str) -> dict | None:
    """
    Salvage tool calls from Groq's tool_use_failed error string.
    Format: <function=name>{'arg': 'val'}</function>
    """
    name_match = re.search(r"<function=(\w+)>", error_str)
    if not name_match:
        return None
    name = name_match.group(1)

    args_match = re.search(r"<function=\w+>(.+?)</function>", error_str, re.DOTALL)
    if not args_match:
        return None
    raw = args_match.group(1).strip()

    try:
        args = json.loads(raw)
    except json.JSONDecodeError:
        try:
            import ast
            args = ast.literal_eval(raw)
        except Exception:
            return None

    return {"id": f"call_{uuid.uuid4().hex[:8]}", "name": name, "args": args}


def chat(
    messages: list[dict],
    tools: list[dict] | None = None,
    system_prompt: str = "",
) -> dict:
    """
    Send a conversation turn to the LLM.

    Returns:
        {"content": str | None, "tool_call": dict | None}

    Retries on rate-limit and connection errors with exponential backoff.
    Falls back to plain chat if tool_use_failed and the call can't be parsed.
    """
    kwargs = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            *messages,
        ],
        "max_tokens": LLM_MAX_TOKENS,
        "temperature": LLM_TEMPERATURE,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    for attempt in range(_MAX_RETRIES):
        try:
            response = client.chat.completions.create(**kwargs)
            message  = response.choices[0].message

            if message.tool_calls:
                tc = message.tool_calls[0]
                return {
                    "content": None,
                    "tool_call": {
                        "id":   tc.id,
                        "name": tc.function.name,
                        "args": json.loads(tc.function.arguments),
                    },
                }

            return {"content": message.content, "tool_call": None}

        except _RETRYABLE as e:
            if attempt < _MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"[LLM] Retryable error ({e.__class__.__name__}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise

        except APIStatusError as e:
            error = str(e)
            if "tool_use_failed" in error or "Failed to call a function" in error:
                parsed = _parse_failed_generation(error)
                if parsed:
                    print(f"[LLM] tool_use_failed — salvaging '{parsed['name']}' call")
                    return {"content": None, "tool_call": parsed}

                print("[LLM] tool_use_failed — falling back to plain chat")
                kwargs.pop("tools", None)
                kwargs.pop("tool_choice", None)
                resp2 = client.chat.completions.create(**kwargs)
                return {"content": resp2.choices[0].message.content, "tool_call": None}

            raise

    # Should not reach here
    raise RuntimeError("[LLM] Exhausted retries without a response")


def quick_extract(prompt: str, system_prompt: str = "") -> str:
    """
    Cheap single-turn call for fact extraction.
    No tools, deterministic, low token budget.
    """
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt or "You are a precise data extractor. Output only valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=200,
        temperature=0.0,
    )
    return response.choices[0].message.content or "{}"
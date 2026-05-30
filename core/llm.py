import json
import re
import time
import uuid

from groq import Groq
from groq import RateLimitError, APIConnectionError, APIStatusError

from config import LLM_API_KEY, LLM_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE

client = Groq(api_key=LLM_API_KEY)

_MAX_RETRIES = 3

# ── Model fallback chain ─────────────────────────────────────────────────────
# If the primary model hits its daily token limit, we automatically step down
# to the next model in the chain. llama-3.1-8b-instant has 500k TPD vs 70b's 100k.
# Both are free on Groq's free tier.
_MODEL_FALLBACK_CHAIN = [
    LLM_MODEL,                  # primary  — llama-3.3-70b-versatile (from config / .env)
    "llama-3.1-8b-instant",     # fallback — 500k TPD, still handles tool calls
]

# Track which model we're currently using so the fallback persists for the
# whole session — we don't flip back and forth on every call.
_current_model_index = 0


def _current_model() -> str:
    return _MODEL_FALLBACK_CHAIN[min(_current_model_index, len(_MODEL_FALLBACK_CHAIN) - 1)]


def _fallback_model() -> bool:
    """
    Step down to the next model in the chain.
    Returns True if a fallback was available, False if already at the end.
    """
    global _current_model_index
    if _current_model_index < len(_MODEL_FALLBACK_CHAIN) - 1:
        _current_model_index += 1
        print(f"[LLM] Falling back to '{_current_model()}' due to rate limit on primary model.")
        return True
    return False


def _is_tpd_limit(error: RateLimitError) -> bool:
    """Distinguish daily token limit (TPD) from per-minute rate limit (TPM)."""
    msg = str(error).lower()
    return "tokens per day" in msg or "tpd" in msg


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

    Model fallback chain:
        llama3-groq-70b (primary) → llama3-groq-8b (fallback on TPD limit)

    Retries transient errors (TPM rate limits, connection errors) with
    exponential backoff. TPD (daily) limits trigger the fallback chain instead.
    """
    kwargs = {
        "model":       _current_model(),
        "messages":    [{"role": "system", "content": system_prompt}, *messages],
        "max_tokens":  LLM_MAX_TOKENS,
        "temperature": LLM_TEMPERATURE,
    }
    if tools:
        kwargs["tools"]       = tools
        kwargs["tool_choice"] = "auto"

    for attempt in range(_MAX_RETRIES):
        # Always use the current model (may have changed due to fallback)
        kwargs["model"] = _current_model()

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

        except RateLimitError as e:
            if _is_tpd_limit(e):
                # Daily limit hit — try the next model in the chain
                if _fallback_model():
                    # Retry immediately with the new model (reset attempt counter)
                    attempt = 0
                    continue
                else:
                    # All models exhausted
                    return {
                        "content": (
                            "I've hit the daily token limit on all available models. "
                            "Things will reset at midnight UTC. You can also check "
                            "usage at console.groq.com."
                        ),
                        "tool_call": None,
                    }
            else:
                # Per-minute rate limit — back off and retry same model
                if attempt < _MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    print(f"[LLM] Rate limit (TPM), retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    return {
                        "content": "I'm being rate-limited right now. Please try again in a moment.",
                        "tool_call": None,
                    }

        except APIConnectionError as e:
            if attempt < _MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"[LLM] Connection error, retrying in {wait}s... ({e})")
                time.sleep(wait)
            else:
                return {
                    "content": "I couldn't reach the AI service. Check your internet connection and try again.",
                    "tool_call": None,
                }

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

    return {"content": "I couldn't get a response — please try again.", "tool_call": None}


def quick_extract(prompt: str, system_prompt: str = "") -> str:
    """
    Cheap single-turn call for fact extraction.
    No tools, deterministic, low token budget.
    Always uses the current active model (respects fallback state).
    """
    try:
        response = client.chat.completions.create(
            model=_current_model(),
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
    except RateLimitError as e:
        if _is_tpd_limit(e):
            _fallback_model()
        return "{}"
    except Exception:
        return "{}"
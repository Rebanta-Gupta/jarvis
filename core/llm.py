from groq import Groq
from config import GROQ_API_KEY, SYSTEM_PROMPT

client = Groq(api_key=GROQ_API_KEY)

def chat(messages: list[dict]) -> str:
    """
    Send a conversation to the LLM and return the reply.
    `messages` is a list of {"role": "user"/"assistant", "content": "..."}
    The system prompt is injected automatically.
    """
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",   # fast + free on Groq
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *messages,
        ],
        max_tokens=512,
        temperature=0.7,
    )
    return response.choices[0].message.content
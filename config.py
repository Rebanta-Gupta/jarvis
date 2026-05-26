from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Jarvis")

SYSTEM_PROMPT = f"""You are {ASSISTANT_NAME}, a personal AI assistant.
You are helpful, concise, and conversational.
When answering voice queries, keep responses short — 1 to 3 sentences unless the user asks for detail.
"""
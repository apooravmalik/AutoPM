# bot/utils/ai_client.py

import os
from openai import AsyncOpenAI # Use the Async client for telegram-bot

# Initialize the OpenAI client to point to the OpenRouter API endpoint
client = AsyncOpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.getenv("OPENROUTER_API_KEY"),
)

def get_ai_client():
    """Returns the initialized OpenRouter client."""
    return client
# bot/utils/ai_client.py

def get_model_name():
    """Returns the name of the model to be used for completions."""
    # We use a fast and capable Llama 3 model from Groq.
    return "groq/llama3-8b-8192"
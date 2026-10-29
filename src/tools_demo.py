"""Function-calling skeleton: the model decides which Python function to call."""
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
model = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")


def get_weather(city: str) -> str:
    """Return the weather for a city."""
    return f"Sunny in {city}"


# NOTE: native tool support for Gemma on the Gemini API may vary by model;
# if this errors, fall back to prompting for JSON and parsing it.
resp = client.models.generate_content(
    model=model,
    contents="What's the weather in Lviv?",
    config=types.GenerateContentConfig(tools=[get_weather]),
)
print(resp.text)

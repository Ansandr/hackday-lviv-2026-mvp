import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
model = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")

response = client.models.generate_content(model=model, contents="Say hi in one sentence.")
print(response.text)

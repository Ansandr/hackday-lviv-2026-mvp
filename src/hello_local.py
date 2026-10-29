import ollama

MODEL = "gemma3:4b"  # adjust to whatever `ollama list` shows

r = ollama.chat(model=MODEL, messages=[{"role": "user", "content": "Say hi in one sentence."}])
print(r["message"]["content"])

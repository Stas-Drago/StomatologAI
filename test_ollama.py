from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

response = client.chat.completions.create(
    model="gemma3:12b-it-qat",
    messages=[{"role": "user", "content": "Привет! Как тебя зовут?"}],
    max_tokens=50
)

print("Ответ модели:", response.choices[0].message.content)
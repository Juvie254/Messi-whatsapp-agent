import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def call_llm(messages, model="groq/compound-mini"):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
        max_tokens=200
    )
    return response.choices[0].message.content.strip()

from openai import OpenAI
import os
import requests
from groq import Groq

print("🔑 GROQ KEY PRESENT:", bool(os.getenv("GROQ_API_KEY")))

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def call_llm(model: str, messages: list):
    response = client.chat.completions.create(
        model="groq/compound-mini",
        messages=messages,
        temperature=0.7
    )

    return {
        "choices": [
            {
                "message": {
                    "content": response.choices[0].message.content
                }
            }
        ]
    }


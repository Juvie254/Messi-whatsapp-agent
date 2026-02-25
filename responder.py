from llm import call_llm

def generate_reply(text, context):

    reply = call_llm(
        messages=[
            {"role": "system", "content": context["system_prompt"]},
            {"role": "user", "content": text},
        ]
    )

    return reply.strip()


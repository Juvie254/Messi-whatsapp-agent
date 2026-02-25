from llm import call_llm
from context_builder import build_system_prompt


# Mock user object (minimal fields needed)
class MockUser:
    def __init__(self):
        self.condition = None
        self.preferred_date = None
        self.preferred_time = None


user = MockUser()
conversation_history = []

is_returning = False


while True:
    msg = input("You: ")

    # Save user message to mock history
    conversation_history.append({"role": "user", "content": msg})

    # Build system prompt
    system_prompt = build_system_prompt(user, is_returning)

    # Construct messages list
    messages = [
        {"role": "system", "content": system_prompt}
    ] + conversation_history

    # Call LLM
    reply = call_llm(messages)

    print(f"\nAgent: {reply}\n")

    # Save assistant reply
    conversation_history.append({"role": "assistant", "content": reply})

    # After first exchange, treat as returning
    is_returning = True

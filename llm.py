import os
import time
import logging

from groq import (
    Groq,
    APIConnectionError,
    APIStatusError,
    NotFoundError,
    RateLimitError,
)

logger = logging.getLogger("amara.llm")

# ---------- Config (all overridable via environment variables) ----------
PRIMARY_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
FALLBACK_MODEL = os.getenv("GROQ_FALLBACK_MODEL", "openai/gpt-oss-20b")
TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.4"))
# gpt-oss models spend part of this budget on hidden reasoning, so keep it generous
MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "1000"))
REASONING_EFFORT = os.getenv("GROQ_REASONING_EFFORT", "low")
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "8"))
RATE_LIMIT_WAIT_SECONDS = float(os.getenv("RATE_LIMIT_WAIT_SECONDS", "2.5"))

HOLDING_MESSAGE = os.getenv(
    "HOLDING_MESSAGE",
    "Thanks for your message! An agent will get back to you shortly.",
)

client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=30.0, max_retries=0)


def _trim_messages(messages):
    """Keep all system messages plus only the most recent conversation turns."""
    system = [m for m in messages if m.get("role") == "system"]
    rest = [m for m in messages if m.get("role") != "system"]
    return system + rest[-MAX_HISTORY_MESSAGES:]


def _call_model(model, messages):
    """One call to one model. Raises on API errors, returns text (may be empty)."""
    kwargs = dict(
        model=model,
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )
    # Reasoning controls only apply to the gpt-oss models
    if "gpt-oss" in model:
        kwargs["extra_body"] = {"reasoning_effort": REASONING_EFFORT}

    response = client.chat.completions.create(**kwargs)

    usage = getattr(response, "usage", None)
    if usage:
        logger.info(
            "LLM usage model=%s prompt=%s completion=%s total=%s",
            model,
            getattr(usage, "prompt_tokens", "?"),
            getattr(usage, "completion_tokens", "?"),
            getattr(usage, "total_tokens", "?"),
        )

    content = response.choices[0].message.content
    return (content or "").strip()


def call_llm(messages, model=None):
    """
    Try the primary model, then the fallback. If everything fails,
    log an alert line and return a holding message so the lead is never left on read.
    """
    messages = _trim_messages(messages)

    models = []
    for m in [model or PRIMARY_MODEL, FALLBACK_MODEL]:
        if m and m not in models:
            models.append(m)

    errors = []

    for model_name in models:
        for attempt in range(2):
            try:
                text = _call_model(model_name, messages)
                if text:
                    return text
                errors.append(f"{model_name}: empty reply (raise GROQ_MAX_TOKENS?)")
                logger.warning("Empty reply from %s", model_name)
                break  # go to next model

            except RateLimitError as e:
                errors.append(f"{model_name}: rate limited")
                logger.warning("Rate limited on %s: %s", model_name, e)
                if attempt == 0:
                    time.sleep(RATE_LIMIT_WAIT_SECONDS)
                    continue  # retry the same model once
                break

            except NotFoundError as e:
                errors.append(f"{model_name}: MODEL NOT FOUND")
                logger.error("Model not found %s: %s", model_name, e)
                break

            except (APIStatusError, APIConnectionError) as e:
                errors.append(f"{model_name}: {type(e).__name__}")
                logger.error("Groq error on %s: %s", model_name, e)
                break

            except Exception as e:
                errors.append(f"{model_name}: unexpected {type(e).__name__}")
                logger.exception("Unexpected error on %s", model_name)
                break

    logger.error("AMARA ALERT: all models failed -> %s", " | ".join(errors))
    return HOLDING_MESSAGE

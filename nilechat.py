"""Bite 1A + 1E + 1F — NileChat brain via HF Space HTTP API, with memory and DB."""
import os
import time
import json
import asyncio
import httpx
from dotenv import load_dotenv
from db import get_or_create_user, get_or_create_conversation, save_message, get_recent_messages

load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY")
SPACE_URL = "https://mbzuai-paris-nile-chat-12b.hf.space"

# Which model answers customers. "nilechat" (default) = Nile-Chat-12B Space.
# "chat_completions" = any provider exposing a /chat/completions endpoint
# (set LLM_BASE_URL, LLM_API_KEY, LLM_MODEL) — swap models without code changes.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "nilechat")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL")

_context_cache: dict[int, list[dict]] = {}
_space_warm = False


async def _call_nilechat(message: str, history: list[dict], system_prompt: str = None) -> str:
    """Call NileChat Space REST API with conversation history."""
    global _space_warm

    if not HF_API_KEY or HF_API_KEY == "your_huggingface_api_key_here":
        raise EnvironmentError("HF_API_KEY missing — set it in .env")

    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    # Convert history to Gradio format: list of [user, bot] pairs
    gradio_history = []
    for i in range(0, len(history) - 1, 2):
        if i + 1 < len(history):
            gradio_history.append([history[i]["content"], history[i + 1]["content"]])

    # Prepend system prompt directly to the message so the model has context
    if system_prompt:
        message = f"{system_prompt}\n\nسؤال العميل: {message}"

    payload = {
        "data": [
            message,        # current message
            gradio_history, # chat history
            1024,           # max_new_tokens
            True,           # do_sample
            0.2,            # temperature (low = sticks to the facts)
            0.9,            # top_p
            50,             # top_k
            1.1,            # repetition_penalty
        ]
    }

    async with httpx.AsyncClient(timeout=180.0, headers=headers) as client:
        # Warm up space on first call
        if not _space_warm:
            try:
                await client.get(SPACE_URL, timeout=30)
                await asyncio.sleep(2)
                _space_warm = True
            except Exception:
                pass

        # Submit job
        r = await client.post(f"{SPACE_URL}/gradio_api/call/chat", json=payload)
        if r.status_code != 200:
            return f"معلش، مشكلة في الاتصال ({r.status_code})"

        event_id = r.json().get("event_id")
        if not event_id:
            return "معلش، مشكلة في الاتصال"

        # Stream result
        last_data = None
        async with client.stream("GET", f"{SPACE_URL}/gradio_api/call/chat/{event_id}", timeout=120) as stream:
            async for line in stream.aiter_lines():
                if not line:
                    continue
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str and data_str != "null":
                        last_data = data_str

        if last_data:
            try:
                parsed = json.loads(last_data)
                if isinstance(parsed, list) and parsed:
                    return str(parsed[-1]) if parsed[-1] else str(parsed[0])
                return str(parsed)
            except json.JSONDecodeError:
                return last_data

        return "مش فاهم — ممكن تعيد؟"


async def _call_chat_completions(message: str, history: list[dict], system_prompt: str = None) -> str:
    """Call a standard /chat/completions endpoint with conversation history."""
    if not (LLM_BASE_URL and LLM_MODEL):
        raise EnvironmentError("LLM_BASE_URL and LLM_MODEL must be set for LLM_PROVIDER=chat_completions")

    messages = [{"role": "system", "content": system_prompt}] if system_prompt else []
    messages += history + [{"role": "user", "content": message}]
    headers = {"Authorization": f"Bearer {LLM_API_KEY}"} if LLM_API_KEY else {}

    async with httpx.AsyncClient(timeout=120.0, headers=headers) as client:
        r = await client.post(
            f"{LLM_BASE_URL}/chat/completions",
            json={"model": LLM_MODEL, "messages": messages, "temperature": 0.6, "max_tokens": 1024},
        )
        if r.status_code != 200:
            return f"معلش، مشكلة في الاتصال ({r.status_code})"
        return r.json()["choices"][0]["message"]["content"]


async def _call_model(message: str, history: list[dict], system_prompt: str = None) -> str:
    if LLM_PROVIDER == "chat_completions":
        return await _call_chat_completions(message, history, system_prompt)
    return await _call_nilechat(message, history, system_prompt)


def _format_history(messages: list[dict]) -> list[dict]:
    return [
        {"role": "user" if m["role"] == "user" else "assistant", "content": m["content"]}
        for m in messages
    ]


async def get_context(conversation_id: int) -> list[dict]:
    """Bite 1F: cached history or load from DB."""
    if conversation_id in _context_cache:
        return _context_cache[conversation_id]
    rows = await get_recent_messages(conversation_id, limit=5)
    history = _format_history(rows)
    _context_cache[conversation_id] = history
    return history


def _update_context_cache(conversation_id: int, user_text: str, bot_reply: str):
    history = _context_cache.get(conversation_id, [])
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": bot_reply})
    _context_cache[conversation_id] = history[-10:]


def _build_system_prompt(company_name: str, knowledge_base: str) -> str:
    return (
        f"أنت مساعد خدمة عملاء لشركة {company_name}. "
        f"ردودك تكون باللغة العربية المصرية فقط، وبأسلوب مهذب ومختصر.\n\n"
        f"معلومات الشركة:\n{knowledge_base}\n\n"
        f"قواعد مهمة:\n"
        f"- رد فقط على الأسئلة المتعلقة بمعلومات الشركة المذكورة أعلاه.\n"
        f"- لو السؤال مش موجود في المعلومات، قول: 'عذراً، مش عندي معلومات عن ده. تواصل مع فريقنا مباشرة.'\n"
        f"- لا تخترع معلومات أو أسعار غير موجودة في المعلومات. قول الأسعار بالظبط زي ما هي مكتوبة.\n"
        f"- متناديش العميل بأي اسم إلا لو هو قال اسمه.\n"
        f"- ابدأ دايماً بالترحيب بالعميل بإسم الشركة {company_name}."
    )


async def reply(
    user_text: str,
    phone: str,
    platform: str = "test",
    name: str = None,
    company_id: int = None,
    company_name: str = None,
    knowledge_base: str = None,
) -> str:
    """Full pipeline: load context → NileChat → save to DB → return reply."""
    user_id = await get_or_create_user(phone, name)
    conv_id = await get_or_create_conversation(user_id, platform, company_id)

    history = await get_context(conv_id)

    system_prompt = None
    if knowledge_base and company_name:
        system_prompt = _build_system_prompt(company_name, knowledge_base)

    bot_reply = await _call_model(user_text, history, system_prompt)

    await save_message(conv_id, "user", user_text)
    await save_message(conv_id, "bot", bot_reply)
    _update_context_cache(conv_id, user_text, bot_reply)

    return bot_reply


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")

    async def _test():
        result = await reply(
            user_text="ازيك يا معلم، عايز أسألك سؤال",
            phone="test_user",
            platform="test",
        )
        from db import close_pool
        await close_pool()
        with open("nilechat_test_result.txt", "w", encoding="utf-8") as f:
            f.write(f"Response: {result}\n")
        print(f"Bot reply saved to nilechat_test_result.txt")

    asyncio.run(_test())

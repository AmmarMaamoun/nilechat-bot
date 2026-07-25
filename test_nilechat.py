"""Bite 1A — Test NileChat via HuggingFace Space REST API."""
import os
import time
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY")
SPACE_URL = "https://mbzuai-paris-nile-chat-12b.hf.space"


def validate_config():
    if not HF_API_KEY or HF_API_KEY == "your_huggingface_api_key_here":
        raise EnvironmentError("HF_API_KEY missing — set it in .env")


def send_message(text: str) -> str:
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    with httpx.Client(timeout=180.0, headers=headers) as client:
        print("Waking up NileChat Space...")
        try:
            client.get(f"{SPACE_URL}/", timeout=30)
        except Exception:
            pass
        time.sleep(3)

        payload = {
            "data": [
                text,   # message
                [],     # chat_history
                1024,   # max_new_tokens
                True,   # do_sample
                0.6,    # temperature
                0.9,    # top_p
                50,     # top_k
                1.1,    # repetition_penalty
            ]
        }

        print("Submitting message...")
        r = client.post(f"{SPACE_URL}/gradio_api/call/chat", json=payload)

        if r.status_code != 200:
            return f"Submit failed {r.status_code}: {r.text[:300]}"

        event_id = r.json().get("event_id")
        print(f"event_id: {event_id}")

        print("Reading stream...")
        all_lines = []
        last_data = None

        with client.stream("GET", f"{SPACE_URL}/gradio_api/call/chat/{event_id}", timeout=120) as stream:
            for line in stream.iter_lines():
                if not line:
                    continue
                all_lines.append(line)

                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str and data_str != "null":
                        last_data = data_str

        # Save raw stream for debugging
        with open("stream_debug.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(all_lines))

        # Parse the last meaningful data chunk
        if last_data:
            try:
                parsed = json.loads(last_data)
                if isinstance(parsed, list) and parsed:
                    return str(parsed[-1]) if parsed[-1] else str(parsed[0])
                return str(parsed)
            except json.JSONDecodeError:
                return last_data

        return "Empty response — see stream_debug.txt"


if __name__ == "__main__":
    print("=== NileChat API Test ===\n")
    validate_config()

    test_message = "ازيك يا معلم، عايز أسألك سؤال"

    try:
        reply = send_message(test_message)
        with open("nilechat_test_result.txt", "w", encoding="utf-8") as f:
            f.write(f"Sent: {test_message}\n\nResponse:\n{reply}\n")
        print("\nDone! Saved to nilechat_test_result.txt")
        print(f"Response length: {len(reply)} chars")
    except Exception as e:
        print(f"\nFAILED: {e}")

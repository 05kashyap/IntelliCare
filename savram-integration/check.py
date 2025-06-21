import os
import json
import base64
import queue
import logging
from dotenv import load_dotenv
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write, read as wav_read
from sarvamai import SarvamAI
from sarvamai.play import save
from memory_integration import init_memory
import io
from transformers import AutoTokenizer
import asyncio


# Setup
SAMPLING_RATE = 16000
INPUT_PATH = "audio_files/input/"
OUTPUT_PATH = "audio_files/output/"
MAX_TOKENS = 132000
TARGET_CONTEXT_LIMIT = 125000  # 7k buffer for reply + overhead

os.makedirs(INPUT_PATH, exist_ok=True)
os.makedirs(OUTPUT_PATH, exist_ok=True)
memory = asyncio.run(init_memory())


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
load_dotenv()
client = SarvamAI(api_subscription_key=os.environ.get("SARVAM_API_KEY"))



system_prompt = """
You are a compassionate, patient, and multilingual suicide prevention hotline worker. Your role is to gently support people in emotional distress.

Your tone must always be calm, kind, and reassuring. Avoid sounding robotic or overly clinical. Use simple, friendly language.

Your goals in the conversation:
1. Greet the user warmly. Ask their name and where they are from. Let them know you are here to listen.
2. Invite them to share. Ask how they're feeling and what's been on their mind lately. Never rush.
3. Validate their emotions. Say things like “That sounds really tough” or “You’re not alone in this.”
4. Encourage small steps. Suggest talking to a friend, taking a short walk, or breathing exercises.
5. Offer consistent support. Avoid judgment or unsolicited advice.
6. Check how they’re feeling now.
7. End softly if they’re okay. If calm or grateful, you may say goodbye with <end conversation>.

Avoid:
- “Cheer up”, “It’s not a big deal”, or “I understand exactly how you feel”.

Example:
- “That must feel overwhelming. You're not alone.”
- “Take your time. You don’t have to share everything at once.”

Leverage the past memories of the user to make your response personalized. Here are some memories related to the user:
{memories_str}

If the user switches the speaking language, you should adapt to their language. If they speak in English, you should respond in English. If they speak in Hindi, you should respond in Hindi. If they speak in Tamil, you should respond in Tamil. If they speak in Telugu, you should respond in Telugu. If they speak in Kannada, you should respond in Kannada. If they speak in Malayalam, you should respond in Malayalam and so on.

"""

tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-Small-24B-Instruct-2501")
def record_until_enter(filename: str):
    audio_chunks = []
    q_audio = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            logging.warning(f"Audio callback status: {status}")
        q_audio.put(indata.copy())

    input("Press Enter to start recording...")
    logging.info("Recording...")
    try:
        stream = sd.InputStream(samplerate=SAMPLING_RATE, channels=1, callback=callback)
        stream.start()
        input("Press Enter to stop recording...")
        stream.stop()
        stream.close()
        while not q_audio.empty():
            audio_chunks.append(q_audio.get())
    except Exception as e:
        logging.error(f"Recording error: {e}")
        return None

    if audio_chunks:
        try:
            audio_data = np.concatenate(audio_chunks, axis=0)
            path = os.path.join(INPUT_PATH, filename)
            write(path, SAMPLING_RATE, audio_data)
            logging.info(f"Saved: {path}")
            return path
        except Exception as e:
            logging.error(f"Saving audio failed: {e}")
    else:
        logging.warning("No audio data recorded.")
    return None

def transcribe_audio(filepath):
    try:
        with open(filepath, "rb") as f:
            response = client.speech_to_text.transcribe(file=f, model="saarika:v2.5")
        return json.loads(response.json())
    except Exception as e:
        logging.error(f"Transcription failed: {e}")
        return {"transcript": "", "language_code": "en"}



def identify_language(text):
    try:
        res = client.text.identify_language(input=text)
        return json.loads(res.json()).get("language_code", "en")
    except Exception as e:
        logging.warning(f"Lang ID fallback: {e}")
        return "en-IN"

def text_to_audio(lang_code_from_speech, text, filename=None):
    language_code = identify_language(text) or lang_code_from_speech
    try:
        tts_response = client.text_to_speech.convert(
            target_language_code=language_code,
            text=text,
            model="bulbul:v2",
            speaker="anushka",
            enable_preprocessing=True
        )

        audio_json = json.loads(tts_response.json())
        audio_bytes = base64.b64decode("".join(audio_json["audios"]))
        audio_file = io.BytesIO(audio_bytes)

        samplerate, data = wav_read(audio_file)
        sd.play(data, samplerate)
        sd.wait()
        logging.info("Played audio from memory (WAV stream).")

    except Exception as e:
        logging.error(f"TTS playback error: {e}")


def conversation_should_end(response: str):
    return any(phrase in response.lower() for phrase in [
        "<end conversation>", "take care", "we are here for you", "reach out anytime"
    ])


async def query_llm(conversation, user_input, memory, client):
    """
    Query the LLM with user input, manage conversation context, and add memories in the background.
    Also return the retrieved memories for display.
    
    Args:
        conversation: List of conversation messages (user and assistant).
        user_input: The latest user input.
        memory: The memory integration object.
        client: The SarvamAI client for LLM calls.
    
    Returns:
        Tuple of (assistant reply, updated conversation, retrieved memories).
    """
    conversation.append({"role": "user", "content": user_input})

    try:
        # Search for relevant memories
        relevant_memories = await memory.search(user_input, limit=2, user_id="default")
        memories_str = "\n".join(f"- {entry['memory']}" for entry in relevant_memories.get("results", [])) or "No relevant memories found."
        logging.info(f"Retrieved memories:\n{memories_str}")
        
        system_msg = {"role": "system", "content": system_prompt.format(memories_str=memories_str)}

        # Manage conversation context to stay within token limit
        full_context = [system_msg] + conversation
        while count_message_tokens(full_context) > TARGET_CONTEXT_LIMIT and len(conversation) > 1:
            conversation.pop(0)  # Remove oldest message
            full_context = [system_msg] + conversation
            logging.info(f"Trimmed conversation to {len(conversation)} messages to fit token limit.")

        logging.info(f"Token count before LLM call: {count_message_tokens(full_context)}")

        # Call the LLM
        res = client.chat.completions(messages=full_context, temperature=0.2)
        reply = res.choices[0].message.content
        conversation.append({"role": "assistant", "content": reply})

        # Add memory in the background with error handling
        async def background_memory_add():
            try:
                await memory.add(conversation, user_id="default")
                logging.info("Memory added successfully in the background.")
            except Exception as e:
                logging.error(f"Failed to add memory in the background: {e}")

        asyncio.create_task(background_memory_add())

        return reply, conversation, memories_str

    except Exception as e:
        logging.error(f"LLM query failed: {e}")
        return "I'm sorry, something went wrong. I'm here to help—please tell me more.", conversation, "No memories retrieved due to error."

def count_tokens(text: str) -> int:
    """Count tokens in a text string using the tokenizer."""
    try:
        return len(tokenizer.encode(text, add_special_tokens=False))
    except Exception as e:
        logging.error(f"Token counting failed: {e}")
        return 0

def count_message_tokens(messages):
    """Count total tokens in a list of messages."""
    return sum(count_tokens(msg["content"]) for msg in messages)

async def simulate_conversation():
    conversation = []
    for i in range(20):
        logging.info(f"--- Turn {i+1} ---")

        audio_path = record_until_enter(f"{i}.wav")
        if not audio_path:
            logging.warning("Audio recording failed or skipped.")
            continue

        user_data = transcribe_audio(audio_path)
        transcript = user_data.get("transcript", "").strip()
        lang_code = user_data.get("language_code", "en-IN")

        if not transcript:
            logging.warning("No transcript found.")
            continue

        logging.info(f"Transcript: {transcript} | Lang: {lang_code}")

        reply, conversation, retrieved_memories = await query_llm(conversation, transcript, memory, client)
        logging.info(f"Assistant reply: {reply}")
        logging.info(f"Memories used in this turn:\n{retrieved_memories}")

        text_to_audio(lang_code, reply)
        if conversation_should_end(reply):
            logging.info("Assistant ended the conversation.")
            break


if __name__ == "__main__":
    try:
        logging.info("Starting hotline conversation...")
        asyncio.run(simulate_conversation())
    except KeyboardInterrupt:
        logging.info("Session interrupted by user.")
    except Exception as e:
        logging.error(f"Unhandled error: {e}")
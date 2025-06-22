import os
import json
import logging
import threading
import time
from dotenv import load_dotenv
from sarvamai import SarvamAI
from sarvamai.play import save
from .memory_integration import init_memory
from transformers import AutoTokenizer

# Setup
SAMPLING_RATE = 16000
INPUT_PATH = "audio_files/input/"
OUTPUT_PATH = "audio_files/output/"
MAX_TOKENS = 132000
TARGET_CONTEXT_LIMIT = 125000  # 7k buffer for reply + overhead

os.makedirs(INPUT_PATH, exist_ok=True)
os.makedirs(OUTPUT_PATH, exist_ok=True)
memory = init_memory()


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
load_dotenv()
client = SarvamAI(api_subscription_key=os.environ.get("SARVAM_API_KEY"))
from transformers import AutoTokenizer

from guardrails.hub import ShieldGemma2B
from guardrails import Guard, OnFailAction

guard_1 = Guard().use(
    ShieldGemma2B, 
    policies=[ShieldGemma2B.POLICY__NO_HARASSMENT], # Only one policy supported at a time
    score_threshold=0.5,
    on_fail=OnFailAction.NOOP
)

guard_2 = Guard().use(
    ShieldGemma2B,
    policies=[ShieldGemma2B.POLICY__NO_DANGEROUS_CONTENT],
    score_threshold=0.5,
    on_fail=OnFailAction.NOOP
    
)


tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-Small-24B-Instruct-2501")

def count_tokens(text: str) -> int:
    return len(tokenizer.encode(text, add_special_tokens=False))

def count_message_tokens(messages):
    return sum(count_tokens(msg["content"]) for msg in messages)


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


def transcribe_audio(filepath):
    try:
        with open(filepath, "rb") as f:
            response = client.speech_to_text.transcribe(file=f, model="saarika:v2.5")
        return json.loads(response.json())
    except Exception as e:
        logging.error(f"Transcription failed: {e}")
        return {"transcript": "", "language_code": "en-IN"}


def query_llm(conversation, user_input):
    conversation.append({"role": "user", "content": user_input})
    try:
        relevant_memories = memory.search(user_input, limit=3, user_id="default")  # fixed typo: defualt → default
        memories_str = "\n".join(f"- {entry['memory']}" for entry in relevant_memories["results"])

        logging.info("Retrieved Memories:")
        for idx, entry in enumerate(relevant_memories["results"]):
            logging.info(f"{idx+1}. {entry['memory']}")

        system_msg = {
            "role": "system",
            "content": system_prompt.format(memories_str=memories_str)
        }

        full_context = [system_msg] + conversation
        print(full_context)

        while count_message_tokens(full_context) > TARGET_CONTEXT_LIMIT:
            if len(conversation) >= 2:
                conversation.pop(0)
                conversation.pop(0)
                full_context = [system_msg] + conversation
            else:
                break

        logging.info(f"Token count before LLM call: {count_message_tokens(full_context)}")

        res = client.chat.completions(messages=full_context, temperature=0.4)
        reply = res.choices[0].message.content
        conversation.append({"role": "assistant", "content": reply})

        # update only alternatively to prevent latency
        if len(full_context)%2 ==0 :
            memory.add(conversation, user_id="default")

        return reply, conversation

    except Exception as e:
        logging.error(f"LLM error: {e}")
        return "I'm here to help. Please try again.", conversation
    
def identify_language(text):
    try:
        res = client.text.identify_language(input=text)
        return json.loads(res.json()).get("language_code", "en")
    except Exception as e:
        logging.warning(f"Lang ID fallback: {e}")
        return "en"

def convert_to_audio_and_save(lang_code_from_speech, text, save_path):
    """Convert text to audio and save to specified path"""
    language_code = identify_language(text) or lang_code_from_speech
    try:
        # print(f"Converting text to audio: '{text[:100]}...' (language: {language_code})")
        # print(f"Save path: {save_path}")
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        raw_audio_response = client.text_to_speech.convert(
            target_language_code=language_code,
            text=text,
            model="bulbul:v2",
            speaker="anushka",
            enable_preprocessing=True,
            speech_sample_rate=SAMPLING_RATE
        )
        
        # print(f"Sarvam TTS conversion completed, saving to: {save_path}")
        save(raw_audio_response, save_path)
        
        # Verify the file was created
        if os.path.exists(save_path):
            file_size = os.path.getsize(save_path)
            print(f"Audio file saved successfully: {save_path} (size: {file_size} bytes)")
        else:
            print(f"ERROR: Audio file was not created: {save_path}")
            
    except Exception as e:
        print(f"Error in convert_to_audio_and_save: {e}")
        import traceback
        traceback.print_exc()
        raise

def conversation_should_end(response: str):
    # Primary end signal as instructed in system prompt
    if "<end conversation>" in response.lower():
        return True
    
    # Additional end signals that indicate natural conversation closure
    end_phrases = [
        "goodbye", "bye", "farewell", "take care", 
        "we are here for you", "reach out anytime",
        "feel free to call", "thank you for calling",
        "stay safe", "wishing you well"
    ]
    
    response_lower = response.lower()
    # Look for end phrases near the end of the response (last 100 characters)
    response_end = response_lower[-100:] if len(response_lower) > 100 else response_lower
    
    return any(phrase in response_end for phrase in end_phrases)


    
# def simulate_conversation(input_audio_path, output_audio_path):
#     """
#     Simulate conversation with given input and output paths
#     """
#     # Initialize messages with system prompt (handled outside query_llm like in code 1)
#     messages = []  # Don't include system prompt here, it's handled inside query_llm
    
#     max_turns = 20
    
#     for i in range(max_turns):
#         logging.info(f"--- Turn {i+1} ---")
        
#         # Get user input through voice transcription
#         try:
#             user_response = json.loads(transcribe_audio(input_audio_path).json())
#             language_code = user_response.get("language_code", "en-IN")
#             transcribed_text = user_response.get("transcript", "").strip()
#         except Exception as e:
#             logging.warning(f"Audio transcription failed or skipped: {e}")
#             continue
            
#         # Check if transcript is valid
#         if not transcribed_text:
#             logging.warning("No transcript found.")
#             continue
            
#         logging.info(f"Transcript: {transcribed_text} | Lang: {language_code}")
        
#         # Get LLM response
#         text_response, messages = query_llm(messages, transcribed_text)
#         logging.info(f"Assistant reply: {text_response}")
        
#         # Convert to audio output
#         convert_to_audio_and_save(language_code, text_response, output_audio_path)
        
#         # Check if conversation should end (using the logic from code 1)
#         if conversation_should_end(text_response):
#             logging.info("Assistant ended the conversation.")
#             break

def process_single_audio_input(input_audio_path, output_audio_path, conversation_history=None):
    """
    Process a single audio input and generate response
    
    Args:
        input_audio_path: Path to input audio file
        output_audio_path: Path where response audio should be saved
        conversation_history: Previous conversation messages (optional)
    
    Returns:
        dict: Contains transcription, response text, language code, and success status
    """
    try:
        logging.info(f"=== Processing single audio input ===")
        logging.info(f"Input: {input_audio_path}")
        logging.info(f"Output: {output_audio_path}")
        
        # Verify input file exists
        if not os.path.exists(input_audio_path):
            error_msg = f"Input audio file does not exist: {input_audio_path}"
            logging.error(f"ERROR: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "transcription": "",
                "response_text": "",
                "language_code": "en-IN",
                "conversation_history": conversation_history or [],
                "should_end": False
            }
        
        # Initialize conversation if not provided (don't include system prompt here, handled inside query_llm)
        if conversation_history is None:
            conversation_history = []  # Don't include system prompt here, it's handled inside query_llm
        
        logging.info(f"Step 1: Transcribing audio...")
        
        # Step 1: Transcribe input audio
        try:
            transcription_response = transcribe_audio(input_audio_path)
            user_response = transcription_response
            
            language_code = user_response.get("language_code", "en-IN")  # Changed default to match simulate_conversation
            transcribed_text = user_response.get("transcript", "").strip()
            
        except Exception as e:
            logging.warning(f"Audio transcription failed or skipped: {e}")
            return {
                "success": False,
                "error": f"Audio transcription failed: {str(e)}",
                "transcription": "",
                "response_text": "",
                "language_code": "en-IN",
                "conversation_history": conversation_history,
                "should_end": False
            }
        
        logging.info(f"Transcript: {transcribed_text} | Lang: {language_code}")
        
        if not transcribed_text:
            logging.warning("No transcript found.")
            return {
                "success": False,
                "error": "No transcription available",
                "transcription": "",
                "response_text": "",
                "language_code": language_code,
                "conversation_history": conversation_history,
                "should_end": False
            }
        
        logging.info(f"Step 2: Getting LLM response...")
        # Step 2: Get LLM response (this runs first and is not blocked by guard rails)
        text_response, updated_conversation = query_llm(conversation_history, transcribed_text)
        logging.info(f"Assistant reply: {text_response}")
        
        # Step 3: Start guard rails in background threads - completely non-blocking
        logging.info(f"Step 3: Starting background guard rail validation...")
        start_guard_rails_background(transcribed_text, text_response)
        
        logging.info(f"Step 4: Converting to audio...")
        # Step 4: Convert response to audio
        convert_to_audio_and_save(language_code, text_response, output_audio_path)
        
        # Check if audio file was created
        audio_created = os.path.exists(output_audio_path)
        logging.info(f"Audio creation result: {audio_created}")
        
        if audio_created:
            file_size = os.path.getsize(output_audio_path)
            logging.info(f"Output audio file: {output_audio_path} (size: {file_size} bytes)")
        
        # Check if conversation should end (using the logic from simulate_conversation)
        should_end_conversation = conversation_should_end(text_response)
        if should_end_conversation:
            logging.info("Assistant ended the conversation.")
        
        result = {
            "success": audio_created,
            "transcription": transcribed_text,
            "response_text": text_response,
            "language_code": language_code,
            "conversation_history": updated_conversation,
            "should_end": should_end_conversation
        }
        
        logging.info(f"=== Processing complete - Success: {result['success']} ===")
        return result
        
    except Exception as e:
        error_msg = f"Exception in process_single_audio_input: {str(e)}"
        logging.error(f"ERROR: {error_msg}")
        import traceback
        logging.error(traceback.format_exc())
        return {
            "success": False,
            "error": error_msg,
            "transcription": "",
            "response_text": "",
            "language_code": "en-IN",
            "conversation_history": conversation_history or [],
            "should_end": False
        }

# Threading-based guard rail validation functions that don't interfere with application flow
def validate_with_guard_background(guard, text, guard_name):
    """
    Validate text with guard in a background thread - completely non-blocking
    This function runs in the background and only logs results without affecting the main flow
    """
    try:
        # Run the guard validation synchronously in this thread
        guard.validate(text)
        logging.info(f"{guard_name} validation passed - no violations detected")
    except Exception as e:
        logging.warning(f"{guard_name} detected potential violation: {str(e)}")
        # Note: We don't take any action here, just log for monitoring purposes

def start_guard_rails_background(user_input, assistant_response):
    """
    Start guard rails validation in background threads - completely non-blocking
    This function starts the threads and returns immediately without waiting
    """
    try:
        # Create and start background threads - these are daemon threads that won't block the application
        user_thread = threading.Thread(
            target=validate_with_guard_background,
            args=(guard_1, user_input, "User Guard (No Harassment)"),
            daemon=True
        )
        
        assistant_thread = threading.Thread(
            target=validate_with_guard_background,
            args=(guard_2, assistant_response, "Assistant Guard (No Dangerous Content)"),
            daemon=True
        )
        
        # Start both threads and return immediately
        user_thread.start()
        assistant_thread.start()
        
        logging.info("Background guard rail validation started")
        
    except Exception as e:
        logging.warning(f"Failed to start background guard rails: {e}")
        # If guard rails fail to start, we continue with the application flow


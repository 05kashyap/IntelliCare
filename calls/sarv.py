from sarvamai import SarvamAI
from dotenv import load_dotenv
from sarvamai.play import save
import json
import os

SAMPLING_RATE = 16000
DURATION = 10
INPUT_PATH = "audio_files/input/"
OUTPUT_PATH = "audio_files/output"

os.makedirs(INPUT_PATH, exist_ok=True)

load_dotenv()

# Get API key from environment
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY")
if not SARVAM_API_KEY:
    raise ValueError("SARVAM_API_KEY environment variable is required")

client = SarvamAI(
    api_subscription_key=SARVAM_API_KEY,
)

system_prompt = """
You are a helpful multilingual suicide hotline worker. Comfort users and ask them how they are feeling. 
Follow the steps, not in any particular order:
1.Greet the user, ask them their name and where they are from. 
2.Ask them why they are feeling down 
3.Tell them to feel better
If you think user has been comforted and the conversation should end, respond with <end conversation>.
"""

def transcribe_input(input_audio_path):
    with open(input_audio_path, "rb") as f:
        response = client.speech_to_text.transcribe(
            file=f,
            model="saarika:v2.5"
        )
    return response


def query_llm(conversation: list[dict], text):
    conversation.append({"role": "user", "content":text})
    response = client.chat.completions(
    messages=conversation, # type: ignore
    temperature=0.2,
    )
    output = response.choices[0].message.content
    conversation.append({"role": "assistant", "content": output})
    return output, conversation

def convert_to_audio_and_save(language_code, text, save_path):
    """Convert text to audio and save to specified path"""
    try:
        print(f"Converting text to audio: '{text[:100]}...' (language: {language_code})")
        print(f"Save path: {save_path}")
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        raw_audio_response = client.text_to_speech.convert(
            target_language_code=language_code,
            text=text,
            model="bulbul:v2",
            speaker="anushka",
            enable_preprocessing=True
        )
        
        print(f"Sarvam TTS conversion completed, saving to: {save_path}")
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

    
def simulate_conversation(input_audio_path, output_audio_path):
    """
    Simulate conversation with given input and output paths
    """
    # loop:
        # model says hello (system message)
        # get user input through voice
        # transcribe (user message)
        # get llm response (assistant response)
        # get audio output 
        
    messages = [
        {"role":"system", "content": system_prompt}
    ]
    
    max_turns = 20
    
    for i in range(max_turns):
        
        user_response = json.loads(transcribe_input(input_audio_path).json())
        language_code = user_response.get("language_code")
        transcribed_text = user_response.get("transcript")
                
        text_response, messages = query_llm(messages, transcribed_text)
        if "<end conversation>" in text_response:
            break
        
        convert_to_audio_and_save(language_code, text_response, output_audio_path)
        break  # For now, just process one turn

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
        print(f"=== Processing single audio input ===")
        print(f"Input: {input_audio_path}")
        print(f"Output: {output_audio_path}")
        
        # Verify input file exists
        if not os.path.exists(input_audio_path):
            error_msg = f"Input audio file does not exist: {input_audio_path}"
            print(f"ERROR: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "transcription": "",
                "response_text": "",
                "language_code": "hi-IN",
                "conversation_history": conversation_history or []
            }
        
        # Initialize conversation if not provided
        if conversation_history is None:
            conversation_history = [{"role": "system", "content": system_prompt}]
        
        print(f"Step 1: Transcribing audio...")
        # Step 1: Transcribe input audio
        transcription_response = transcribe_input(input_audio_path)
        user_response = json.loads(transcription_response.json())
        
        language_code = user_response.get("language_code", "hi-IN")
        transcribed_text = user_response.get("transcript", "")
        
        print(f"Transcription result - Language: {language_code}, Text: '{transcribed_text}'")
        
        if not transcribed_text:
            error_msg = "No transcription available"
            print(f"ERROR: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "transcription": "",
                "response_text": "",
                "language_code": language_code,
                "conversation_history": conversation_history
            }
        
        print(f"Step 2: Getting LLM response...")
        # Step 2: Get LLM response
        text_response, updated_conversation = query_llm(conversation_history, transcribed_text)
        print(f"LLM response: '{text_response}'")
        
        print(f"Step 3: Converting to audio...")
        # Step 3: Convert response to audio
        convert_to_audio_and_save(language_code, text_response, output_audio_path)
        
        # Check if audio file was created
        audio_created = os.path.exists(output_audio_path)
        print(f"Audio creation result: {audio_created}")
        
        if audio_created:
            file_size = os.path.getsize(output_audio_path)
            print(f"Output audio file: {output_audio_path} (size: {file_size} bytes)")
        
        result = {
            "success": audio_created,
            "transcription": transcribed_text,
            "response_text": text_response,
            "language_code": language_code,
            "conversation_history": updated_conversation,
            "should_end": "<end conversation>" in text_response
        }
        
        print(f"=== Processing complete - Success: {result['success']} ===")
        return result
        
    except Exception as e:
        error_msg = f"Exception in process_single_audio_input: {str(e)}"
        print(f"ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": error_msg,
            "transcription": "",
            "response_text": "",
            "language_code": "hi-IN",
            "conversation_history": conversation_history or []
        }


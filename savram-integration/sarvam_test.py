from sarvamai import SarvamAI
from dotenv import load_dotenv
import sounddevice as sd
from scipy.io.wavfile import write
import scipy.io.wavfile as wav
import time
from sarvamai.play import save
import base64
import io
import json
import queue
import threading
import os
import numpy as np

SAMPLING_RATE = 16000
DURATION = 10
INPUT_PATH = "audio_files/input/"
OUTPUT_PATH = "audio_files/output"

os.makedirs(INPUT_PATH, exist_ok=True)

load_dotenv()
client = SarvamAI(
    api_subscription_key=os.environ.get("SARVAM_API_KEY"),
)

system_prompt = """
You are a helpful multilingual suicide hotline worker. Comfort users and ask them how they are feeling. 
Follow the steps, not in any particular order:
1.Greet the user, ask them their name and where they are from. 
2.Ask them why they are feeling down 
3.Tell them to feel better
If you think user has been comforted and the conversation should end, respond with <end conversation>.
"""

# def record_and_transcribe(conversation_turn):
#     savepath = os.path.join(INPUT_PATH, f"{conversation_turn}.wav")

#     q_audio = queue.Queue()
#     audio_chunks = []
#     recording = True
#     start_time = None

#     def audio_callback(indata, frames, time_info, status):
#         if status:
#             print(status)
#         q_audio.put(indata.copy())

#     def record_audio():
#         nonlocal start_time
#         with sd.InputStream(samplerate=SAMPLING_RATE, channels=1, callback=audio_callback):
#             start_time = time.time()
#             print("Recording... Press 'q' then Enter to stop.")
#             while recording:
#                 sd.sleep(100)

#     input("Press Enter to start recording...")
    
#     thread = threading.Thread(target=record_audio)
#     thread.start()

#     while True:
#         if input().strip().lower() == 'q':
#             recording = False
#             break

#     thread.join()

#     # Collect audio
#     while not q_audio.empty():
#         try:
#             chunk = q_audio.get_nowait()
#             audio_chunks.append(chunk)
#         except queue.Empty:
#             break

#     audio_data = np.concatenate(audio_chunks, axis=0)
#     duration = time.time() - start_time # type: ignore
#     print(f"Recording stopped. Duration: {duration:.2f} seconds")

#     write(savepath, SAMPLING_RATE, audio_data)
#     print(f"Audio saved to {savepath}")

#     with open(savepath, "rb") as f:
#         response = client.speech_to_text.transcribe(
#             file=f,
#             model="saarika:v2.5"
#         )
#     return response


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
    raw_audio_response = client.text_to_speech.convert(
      target_language_code=language_code,
      text=text,
      model="bulbul:v2",
      speaker="anushka",
      enable_preprocessing=True
    )

    save(raw_audio_response, save_path)

    
def simulate_conversation():
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
        
        user_response = json.loads(transcribe_input(input_path_audio).json())
        language_code = user_response.get("language_code")
        transcribed_text = user_response.get("transcript")
                
        text_response, messages = query_llm(messages, transcribed_text)
        if "<end conversation>" in text_response:
            break
        
        convert_to_audio_and_save(language_code, text_response, save_path)
        
        

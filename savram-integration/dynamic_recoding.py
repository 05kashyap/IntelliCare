import sounddevice as sd
import numpy as np
import queue
import threading
import time
import os
from scipy.io.wavfile import write

SAMPLING_RATE = 16000
CHANNELS = 1
INPUT_PATH = "audio_files/input/"
FILENAME = "dynamic_recording.wav"

os.makedirs(INPUT_PATH, exist_ok=True)
savepath = os.path.join(INPUT_PATH, FILENAME)

q_audio = queue.Queue()
recording = True
start_time = None

def audio_callback(indata, frames, time_info, status):
    if status:
        print(status)
    q_audio.put(indata.copy())

def record_audio():
    global start_time
    with sd.InputStream(samplerate=SAMPLING_RATE, channels=CHANNELS, callback=audio_callback):
        start_time = time.time()
        print("Recording... Press 'q' then Enter to stop.")
        while recording:
            sd.sleep(100)  # check every 100ms

def collect_audio():
    audio_chunks = []
    while recording or not q_audio.empty():
        try:
            data = q_audio.get(timeout=0.1)
            audio_chunks.append(data)
        except queue.Empty:
            pass
    return np.concatenate(audio_chunks)

input("Press Enter to start recording...")
thread = threading.Thread(target=record_audio)
thread.start()

# Wait for stop signal
while True:
    if input().strip().lower() == 'q':
        recording = False
        break

thread.join()
audio_data = collect_audio()

duration = time.time() - start_time # type: ignore
print(f"Recording stopped. Duration: {duration:.2f} seconds")

write(savepath, SAMPLING_RATE, audio_data)
print(f"Audio saved to {savepath}")

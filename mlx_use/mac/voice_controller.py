import pvporcupine
from pvrecorder import PvRecorder
import pvleopard
import numpy as np
import os
import time

from mlx_use.controller.service import Controller

from dotenv import load_dotenv
load_dotenv()

# You must set your Picovoice AccessKey as an environment variable or replace this with your key
ACCESS_KEY = os.getenv('PICOVOICE_ACCESS_KEY')

# Use the built-in 'stop' keyword or a custom .ppn file if you have one
KEYWORDS = ['hey siri','stop']  # You can add more keywords if needed

class VoiceMacController:
    def __init__(self):
        self.porcupine = pvporcupine.create(access_key=ACCESS_KEY, keywords=[KEYWORDS[0], KEYWORDS[1]])
        self.recorder = PvRecorder(device_index=-1, frame_length=self.porcupine.frame_length)
        self.leopard = pvleopard.create(access_key=ACCESS_KEY)
        self.controller = Controller()
        self.running = True

    def listen(self):
        print(f"Say '{KEYWORDS[0]}' to start. Say '{KEYWORDS[1]}' to stop.")
        self.recorder.start()
        try:
            while self.running:
                pcm = self.recorder.read()
                keyword_index = self.porcupine.process(pcm)
                if keyword_index == 0:  # WAKE_WORD detected
                    print("Wake word detected! Listening for command...")
                    command = self.record_and_transcribe()
                    print(f"Recognized command: {command}")
                    self.handle_command(command)
                elif keyword_index == 1:  # STOP_WORD detected
                    print("Stop word detected. Exiting.")
                    self.running = False
        finally:
            self.recorder.stop()
            self.porcupine.delete()
            self.recorder.delete()
            self.leopard.delete()

    def record_and_transcribe(self, record_seconds=3):
        print(f"Recording for {record_seconds} seconds...")
        sample_rate = self.leopard.sample_rate
        frame_length = self.porcupine.frame_length
        frames = []
        start_time = time.time()
        while time.time() - start_time < record_seconds:
            frames.append(self.recorder.read())
        # Flatten and convert to int16 numpy array
        audio_data = np.concatenate(frames).astype(np.int16)
        transcript, _ = self.leopard.process(audio_data)
        return transcript.strip()

    def handle_command(self, command):
        # TODO: Map recognized command to Controller actions
        print(f"(Placeholder) Would execute: {command}")
        # Example: if command.lower().startswith('open notes'):
        #     import asyncio
        #     asyncio.run(self.controller.open_app('Notes'))

if __name__ == "__main__":
    VoiceMacController().listen() 
import os
import sys
import threading
import queue
from voice_controller import VoiceMacController

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import argparse
import asyncio
import select

from mlx_use import Agent
from pydantic import SecretStr
from mlx_use.controller.service import Controller


def set_llm(llm_provider:str = None):
	if not llm_provider:
		raise ValueError("No llm provider was set")
	
	if llm_provider == "OAI" and os.getenv('OPENAI_API_KEY'):
		return ChatOpenAI(model='gpt-4', api_key=SecretStr(os.getenv('OPENAI_API_KEY')))
	
	if llm_provider == "google" and os.getenv('GEMINI_API_KEY'):
		return ChatGoogleGenerativeAI(model='gemini-2.0-flash-exp', api_key=SecretStr(os.getenv('GEMINI_API_KEY')))
	
	if llm_provider == "anthropic" and os.getenv('ANTHROPIC_API_KEY'):
		return ChatAnthropic(model='claude-3-sonnet-20240229', api_key=SecretStr(os.getenv('ANTHROPIC_API_KEY')))
	
	return None

def listen_for_command(self, queue):
    self.recorder.start()
    try:
        while self.running:
            pcm = self.recorder.read()
            keyword_index = self.porcupine.process(pcm)
            if keyword_index == 0:  # Wake word detected
                print("Wake word detected! Listening for command...")
                command = self.record_and_transcribe()
                print(f"Recognized command: {command}")
                queue.put(command)
                break
            elif keyword_index == 1:  # Stop word detected
                print("Stop word detected. Exiting.")
                self.running = False
                queue.put(None)
                break
    finally:
        self.recorder.stop()
        self.porcupine.delete()
        self.recorder.delete()
        self.leopard.delete()

# Try to set LLM based on available API keys
llm = None
if os.getenv('GEMINI_API_KEY'):
	llm = set_llm('google')
elif os.getenv('OPENAI_API_KEY'):
	llm = set_llm('OAI')
elif os.getenv('ANTHROPIC_API_KEY'):
	llm = set_llm('anthropic')

if not llm:
	raise ValueError("No API keys found. Please set at least one of GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY in your .env file")

controller = Controller()


async def main():
    agent_greeting = Agent(
        task='Say "Hi there $whoami,  What can I do for you today?"',
        llm=llm,
        controller=controller,
        use_vision=False,
        max_actions_per_step=1,
        max_failures=5
    )
    await agent_greeting.run(max_steps=25)

    # Set up a queue for communication
    command_queue = queue.Queue()
    voice_controller = VoiceMacController()

    # Start the voice controller in a background thread
    voice_thread = threading.Thread(target=voice_controller.listen_for_command, args=(command_queue,))
    voice_thread.start()

    # Wait for either text input or voice input
    print("You can either type your task or say it after the wake word.")
    task = None
    while task is None:
        try:
            # Check if voice command is available
            task = command_queue.get_nowait()
            if task is not None:
                print(f"Voice command received: {task}")
                break
        except queue.Empty:
            pass
        # Non-blocking input (Python 3.8+ on Unix: use input() in a thread, or use select for advanced)
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            task = input("Enter the task: ")
            break

    # Clean up the voice thread if still running
    voice_controller.running = False
    voice_thread.join(timeout=1)

    if not task:
        print("No command received or stopped by user.")
        sys.exit(0)

    agent_task = Agent(
        task=task,
        llm=llm,
        controller=controller,
        use_vision=False,
        max_actions_per_step=4,
        max_failures=5
    )
    await agent_task.run(max_steps=25)


asyncio.run(main())

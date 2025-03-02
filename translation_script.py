from env import DEEPL_ACCESS_KEY, OPENAI_API_KEY
import requests
import os
import time
import sys
import warnings
import tempfile
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np

# AI tool
from openai import OpenAI

# Constants
DEEPL_API_URL = "https://api-free.deepl.com/v2/translate"
MODEL_NAME = "gpt-4o-mini"
MAX_TOKENS = 500
SAMPLE_RATE = 44100  # Audio sample rate
AUDIO_DURATION = 15  # Default recording duration in seconds
INPUT_MODES = ["text", "voice"]  # Available input modes

# Suppress FP16 warning for whisper
warnings.filterwarnings(
    "ignore", message="FP16 is not supported on CPU; using FP32 instead"
)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# System prompt based on the anatomy structure
SYSTEM_PROMPT = """
Goal
I want a Spanish teaching assistant that helps me understand Spanish sentences by breaking them down \
into their components and explaining the translation process to English. I am already an intermediate \
Spanish speaker and want to move from broken Spanish to greak Spanish.

Return Format
For each Spanish sentence I provide, return:
1. The complete English translation
2. A sentence breakdown with literal meanings
3. Explanation of verb conjugations used
4. Identification of grammatical structures
5. Notes on any important differences between Spanish and English syntax

Warnings
Be careful to explain actual definitions rather than just translations. Highlight false cognates \
and common misunderstandings. Ensure conjugation explanations are accurate. Do not return markdown text

--

Context dump
For context: I'm an English speaker learning Spanish. I've studied basics but struggle \
with understanding how Spanish sentences are constructed. I want to fully understand the \
mechanics behind translations rather than just memorizing phrases. I'm particularly interested \
in verb conjugations and grammatical differences between the languages. I learn best when I can see \
exactly how each part of a sentence functions. Please always answer in English unless I specifically \
request Spanish examples.
"""


def get_translation(text: str):
    """Translate Spanish text to English using DeepL API"""
    try:
        response = requests.post(
            url=DEEPL_API_URL,
            headers={'Authorization': 'DeepL-Auth-Key ' + DEEPL_ACCESS_KEY},
            data={"text": [text], "target_lang": "EN", "source_lang": "ES"},
            timeout=30,
        )

        if response.status_code == 200:
            return str(response.json()["translations"][0]["text"]).replace("\n", " ")
        print(f"Translation error: {response.status_code} - {response.reason}")
        return None
    except Exception as e:
        print(f"Exception during translation: {str(e)}")
        return None


def get_explanation(context: list[dict]):
    """Get explanation from OpenAI"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME, messages=context, max_tokens=MAX_TOKENS
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error getting explanation: {str(e)}")
        return "Could not generate explanation."


def print_separator():
    """Print a separator line for better readability"""
    print("*\n* * * * * * * * * * * * * * * * * * * * * * * * * * *\n*")


def record_audio(duration=AUDIO_DURATION):
    """Record audio from microphone for specified duration"""
    print(f"***   Recording for {duration} seconds... Speak now")

    # Record audio
    recording = sd.rec(
        int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32'
    )

    # Display countdown
    for i in range(duration, 0, -1):
        print(f"***   {i}...", end="\r")
        time.sleep(1)

    # Wait until recording is finished
    sd.wait()
    print("***   Recording finished!")

    # Create temporary file for the recording
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        temp_filename = temp_audio.name
        # Normalize and convert to int16
        recording = np.int16(recording * 32767)
        write(temp_filename, SAMPLE_RATE, recording)

    return temp_filename


def transcribe_audio(audio_file_path):
    """Transcribe audio file using OpenAI Whisper API"""
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="es",  # Specify Spanish for better accuracy
            )

        # Clean up the temporary file
        os.remove(audio_file_path)

        return transcription.text
    except Exception as e:
        print(f"Error transcribing audio: {str(e)}")
        return None


def get_input_mode():
    """Get the user's preferred input mode"""
    while True:
        print("***   Input modes: [1] Text | [2] Voice | [q] Quit")
        choice = input("***   Select input mode: ").lower()

        if choice == 'q':
            return None
        elif choice in ['1', 't', 'text']:
            return "text"
        elif choice in ['2', 'v', 'voice']:
            return "voice"
        else:
            print("***   Invalid choice. Please try again.")


def get_spanish_input(mode):
    """Get Spanish input based on the selected mode"""
    if mode == "text":
        return input("***   Enter Spanish text: ")
    elif mode == "voice":
        # Record and transcribe audio
        audio_file = record_audio()
        transcription = transcribe_audio(audio_file)

        if transcription:
            print(f"***   Transcribed: {transcription}")
            confirm = input("***   Is this correct? (y/n): ").lower()

            if confirm == 'y':
                return transcription
            else:
                print("***   Let's try again.")
                return None
        else:
            print("***   Failed to transcribe audio. Please try again.")
            return None

    return None


def main():
    print_separator()

    current_mode = "text"  # Default input mode

    while True:
        # Allow changing input mode
        mode_choice = get_input_mode()
        if not mode_choice:
            break

        current_mode = mode_choice
        print(f"***   Using {current_mode.upper()} input mode")

        # Initialize context with system prompt
        context = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Get Spanish input based on selected mode
        spanish_input = get_spanish_input(current_mode)
        if not spanish_input:
            continue

        if spanish_input.lower() == 'quit':
            break

        # Get translation
        translation = get_translation(spanish_input)
        if not translation:
            print("Could not translate the text. Please try again.")
            continue

        print_separator()
        print(f"***   Translation: {translation}\n*")

        # Build the request for explanation
        full_translation_string = f"Analyze this Spanish sentence: '{spanish_input}' which translates to English as: '{translation}'"
        context.append({"role": "user", "content": full_translation_string})

        # Get detailed explanation
        explanation = get_explanation(context)
        print(f"***   Explanation: {explanation}\n*")

        # Add the explanation to context
        context.append({"role": "assistant", "content": explanation})

        # Q&A mode
        response = input("***   Ask follow-up questions? (y/n): ")
        if response.lower() == 'y':
            while True:
                question = input("***   Question (or 'back' to return): ")

                if question.lower() in ['back', 'b', 'exit', 'quit']:
                    break

                if len(question.strip()) <= 3:
                    continue

                print("***")
                context.append({"role": "user", "content": question})
                answer = get_explanation(context)
                print(f"***   Answer: {answer}\n*")

                # Add Q&A to context
                context.append({"role": "assistant", "content": answer})

        print_separator()


if __name__ == "__main__":
    print("\n* * *  Spanish Learning Assistant  * * *\n")
    print("This application supports text and voice input modes.")
    print("You can speak Spanish and get explanations in English.")

    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting the program. ¡Adiós!")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        # Clean up any temporary files that might be left
        temp_dir = tempfile.gettempdir()
        for file in os.listdir(temp_dir):
            if file.endswith(".wav") and os.path.isfile(os.path.join(temp_dir, file)):
                try:
                    os.remove(os.path.join(temp_dir, file))
                except:
                    pass
        print("\nProgram ended.")

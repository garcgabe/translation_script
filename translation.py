from env import DEEPL_ACCESS_KEY, OPENAI_API_KEY, ELEVEN_LABS_API_KEY
import requests
import os
import time
import warnings
import tempfile
import threading
import traceback
from typing import Optional, List, Dict, Any

import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
from openai import OpenAI
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings


from prompts import CONVO_PROMPT, TEXT_PROMPT

# Constants
DEEPL_API_URL = "https://api-free.deepl.com/v2/translate"
OPENAI_TEXT_MODEL = "gpt-4o-mini"
OPENAI_AUDIO_MODEL = "whisper-1"
MAX_TOKENS = 1500
SAMPLE_RATE = 44100  # Audio sample rate
MAX_RECORD_TIME = 60  # Maximum recording time in seconds
INPUT_MODES = ["text", "voice", "conversation"]  # Available input modes

# Suppress FP16 warning for whisper
warnings.filterwarnings(
    "ignore", message="FP16 is not supported on CPU; using FP32 instead"
)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


def print_separator() -> None:
    """Print a separator line for better readability"""
    print("*\n* * * * * * * * * * * * * * * * * * * * * * * * * * *\n*")


class AudioRecorder:
    """Handles audio recording functionality"""
    
    def __init__(self, sample_rate: int = SAMPLE_RATE, max_record_time: int = MAX_RECORD_TIME):
        self.sample_rate = sample_rate
        self.max_record_time = max_record_time
    
    def record_audio(self) -> Optional[str]:
        """Record audio using a simple start/stop approach with ENTER key"""
        print("***   Press ENTER to start recording...")
        input()  # Wait for Enter key

        print("***   Recording... Press ENTER to stop")
        print(f"***   (Recording will automatically stop after {self.max_record_time} seconds)")

        # Start recording
        recording = sd.rec(
            int(self.max_record_time * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
        )

        # Create a separate thread to wait for key press
        stop_recording = False

        def wait_for_enter():
            nonlocal stop_recording
            input()  # Wait for Enter key
            stop_recording = True

        input_thread = threading.Thread(target=wait_for_enter)
        input_thread.daemon = True
        input_thread.start()

        # Show recording progress until Enter is pressed or max time is reached
        start_time = time.time()
        frame_index = 0

        while not stop_recording and frame_index < len(recording):
            elapsed = time.time() - start_time
            print(f"***   Recording: {elapsed:.1f}s", end="\r")
            time.sleep(0.1)
            frame_index = int(elapsed * self.sample_rate)

            if elapsed >= self.max_record_time:
                break

        # Calculate actual duration
        duration = time.time() - start_time

        # Stop recording
        sd.stop()
        print(f"\n***   Recording finished! Duration: {duration:.1f} seconds")

        # Trim recording to actual duration
        actual_frames = int(duration * self.sample_rate)
        trimmed_recording = recording[:actual_frames]

        # Create temporary file for the recording
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            temp_filename = temp_audio.name
            # Normalize and convert to int16
            trimmed_recording = np.int16(trimmed_recording * 32767)
            write(temp_filename, self.sample_rate, trimmed_recording)

        return temp_filename


class TranslationService:
    """Handles translation services"""
    
    def __init__(self, api_key: str, api_url: str = DEEPL_API_URL):
        self.api_key = api_key
        self.api_url = api_url
    
    def translate(self, text: str, source_lang: str = "ES", target_lang: str = "EN") -> Optional[str]:
        """Translate text using DeepL API"""
        try:
            response = requests.post(
                url=self.api_url,
                headers={'Authorization': 'DeepL-Auth-Key ' + self.api_key},
                data={"text": [text], "target_lang": target_lang, "source_lang": source_lang},
                timeout=30,
            )

            if response.status_code == 200:
                return str(response.json()["translations"][0]["text"]).replace("\n", " ")
            else:
                print(f"Translation error: {response.status_code} - {response.reason}")
                return None
        except Exception as e:
            print(f"Exception during translation: {str(e)}")
            return None


class AIService:
    """Handles AI services including text and speech"""
    
    def __init__(self, api_key: str, text_model: str = OPENAI_TEXT_MODEL, audio_model: str = OPENAI_AUDIO_MODEL):
        self.client = OpenAI(api_key=api_key)
        self.text_model = text_model
        self.audio_model = audio_model
        self.elevenlabs_client = ElevenLabs(api_key=ELEVEN_LABS_API_KEY)
    
    def get_text_completion(self, context: List[Dict[str, str]], max_tokens: int = MAX_TOKENS) -> str:
        """Get text completion from OpenAI"""
        try:
            completion = self.client.chat.completions.create(
                model=self.text_model, 
                messages=context, 
                max_tokens=max_tokens
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error getting explanation: {str(e)}")
            return "Could not generate explanation."
    
    def transcribe_audio(self, audio_file_path: str, language: str = "es") -> Optional[str]:
        """Transcribe audio file using OpenAI Whisper API"""
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model=self.audio_model,
                    file=audio_file,
                    language=language,
                )

            # Clean up the temporary file
            os.remove(audio_file_path)

            return transcription.text
        except Exception as e:
            print(f"Error transcribing audio: {str(e)}")
            return None
    
    def text_to_speech(self, text: str) -> Optional[str]:
        """
        Convert text to speech using OpenAI's TTS API
        
        Args:
            text: The text to convert to speech
            voice: The voice to use (options: alloy, echo, fable, onyx, nova, shimmer)
            
        Returns:
            Path to the audio file or None if there was an error
        """
        try:
            response = self.elevenlabs_client.text_to_speech.convert(
                voice_id="21m00Tcm4TlvDq8ikWAM",  # Adam pre-made voice
                optimize_streaming_latency="0",
                output_format="mp3_22050_32",
                text=text,
                model_id="eleven_multilingual_v2",  # Use turbo model for low latency, for other languages use `eleven_multilingual_v2`
                voice_settings=VoiceSettings(
                    stability=0.5,
                    similarity_boost=0.75,
                    style=0.15,
                    speed=0.75
                ),
            )

            # Save the streamed audio to a temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
                temp_filename = temp_audio.name

                # Iterate over the generator to write chunks to file
                for chunk in response:
                    temp_audio.write(chunk)

            return temp_filename
            
        except Exception as e:
            print(f"Error in text-to-speech conversion: {str(e)}")
            return None
    
    def play_audio(self, audio_file_path: str) -> bool:
        """
        Play an audio file
        
        Args:
            audio_file_path: Path to the audio file to play
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # TODO: Implement audio playback functionality
            # This is a placeholder for audio playback
            
            # Example implementation with a system call (platform dependent):
            import subprocess
            subprocess.call(["afplay", audio_file_path])  # macOS
            
            #print(f"Playing audio from {audio_file_path}")
            #print("Audio playback functionality to be implemented")
            return True
            
        except Exception as e:
            print(f"Error playing audio: {str(e)}")
            return False


class SpanishLearningAssistant:
    """Main class that handles the Spanish learning assistant functionality"""
    
    def __init__(self):
        self.translator = TranslationService(DEEPL_ACCESS_KEY)
        self.ai_service = AIService(OPENAI_API_KEY)
        self.audio_recorder = AudioRecorder()
        self.current_mode = "text"  # Default input mode
    
    def get_input_mode(self) -> Optional[str]:
        """Get the user's preferred input mode"""
        while True:
            print("***   Input modes: [1] Text | [2] Voice | [3] Conversation | [q] Quit")
            choice = input("***   Select input mode: ").lower()

            if choice == 'q':
                return None
            elif choice in ['1', 't', 'text']:
                return "text"
            elif choice in ['2', 'v', 'voice']:
                return "voice"
            elif choice in ['3', 'c', 'conversation']:
                return "conversation"
            else:
                print("***   Invalid choice. Please try again.")
    
    def get_spanish_input(self, mode: str) -> Optional[str]:
        """Get Spanish input based on the selected mode"""
        if mode == "text":
            return input("***   Enter Spanish text: ")
        elif mode == "voice":
            # Record audio
            audio_file = self.audio_recorder.record_audio()

            if not audio_file:
                return None

            transcription = self.ai_service.transcribe_audio(audio_file)

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
    
    def conversation_mode(self) -> None:
        """Handle conversation mode with AI agent using voice or text"""
        print_separator()
        print("***   Starting conversation mode")
        print("***   You can speak in Spanish, and the AI will respond.")
        print("***   Type 'exit' or 'back' at any time to return to the main menu")

        # Ask once for input mode
        while True:
            input_type = input("***   Choose input mode: [v]oice or [t]ext: ").strip().lower()
            if input_type.startswith('v'):
                mode = 'voice'
                break
            elif input_type.startswith('t'):
                mode = 'text'
                break
            else:
                print("***   Invalid option. Please enter 'v' or 't'.")

        context = [{"role": "system", "content": CONVO_PROMPT}]

        while True:
            user_input = None

            if mode == 'voice':
                audio_file = self.audio_recorder.record_audio()
                if audio_file:
                    user_input = self.ai_service.transcribe_audio(audio_file)
                    if user_input:
                        print(f"***   You said: {user_input}")
            else:
                user_input = input("***   Your message: ")

            if not user_input or user_input.lower() in ['back', 'exit']:
                break

            # Translate if needed
            translation = self.translator.translate(user_input)
            if translation:
                print(f"***   Translation: {translation}")

            context.append({"role": "user", "content": user_input})
            response = self.ai_service.get_text_completion(context)
            print(f"***   AI: {response}")

            speech_file = self.ai_service.text_to_speech(response)
            if speech_file:
                self.ai_service.play_audio(speech_file)
                os.remove(speech_file)

            context.append({"role": "assistant", "content": response})
            print_separator()

    def translation_mode(self, mode: str) -> None:
        """Handle translation and explanation mode"""
        # Initialize context with system prompt
        context = [{"role": "system", "content": TEXT_PROMPT}]

        # Get Spanish input based on selected mode
        spanish_input = self.get_spanish_input(mode)
        if not spanish_input:
            return

        if spanish_input.lower() in ['quit', 'exit', 'back']:
            return

        # Get translation
        translation = self.translator.translate(spanish_input)
        if not translation:
            print("Could not translate the text. Please try again.")
            return

        print_separator()
        print(f"***   Translation: {translation}\n*")

        # # Build the request for explanation
        # full_translation_string = f"Analyze this Spanish sentence: '{spanish_input}' which translates to English as: '{translation}'"
        # context.append({"role": "user", "content": full_translation_string})

        # # Get detailed explanation
        # explanation = self.ai_service.get_text_completion(context)
        # print(f"***   Explanation: {explanation}\n*")

        # # Add the explanation to context
        # context.append({"role": "assistant", "content": explanation})

        # # Q&A mode
        # response = input("***   Ask follow-up questions? (y/n): ")
        # if response.lower() == 'y':
        #     while True:
        #         question = input("***   Question (or 'back' to return): ")

        #         if question.lower() in ['back', 'b', 'exit', 'quit']:
        #             break

        #         if len(question.strip()) <= 3:
        #             continue

        #         print("***")
        #         context.append({"role": "user", "content": question})
        #         answer = self.ai_service.get_text_completion(context)
        #         print(f"***   Answer: {answer}\n*")

        #         # Add Q&A to context
        #         context.append({"role": "assistant", "content": answer})

        print_separator()
    
    def run(self) -> None:
        """Main loop for the Spanish learning assistant"""
        print_separator()

        while True:
            # Allow changing input mode
            mode_choice = self.get_input_mode()
            if not mode_choice:
                break

            self.current_mode = mode_choice
            print(f"***   Using {self.current_mode.upper()} input mode")

            if self.current_mode == "conversation":
                self.conversation_mode()
            else:
                self.translation_mode(self.current_mode)


def cleanup_temp_files() -> None:
    """Clean up any temporary files that might be left"""
    temp_dir = tempfile.gettempdir()
    for file in os.listdir(temp_dir):
        if file.endswith((".wav", ".mp3")) and os.path.isfile(os.path.join(temp_dir, file)):
            try:
                os.remove(os.path.join(temp_dir, file))
            except:
                pass


def main() -> None:
    """Main function to run the application"""
    print("\n* * *  Spanish Learning Assistant  * * *\n")
    print("This application supports text, voice input, and conversation modes.")
    print("You can speak Spanish and get explanations in English.")
    print("In voice mode, press ENTER to start recording, then ENTER again to stop.")
    print("In conversation mode, you can have a dialog with an AI assistant.")

    try:
        assistant = SpanishLearningAssistant()
        assistant.run()
    except KeyboardInterrupt:
        print("\n\nExiting the program. ¡Adiós!")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        traceback.print_exc()
    finally:
        cleanup_temp_files()
        print("\nProgram ended.")


if __name__ == "__main__":
    main()
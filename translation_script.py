from env import DEEPL_ACCESS_KEY
import requests
import os, time

# text to speech
from gtts import gTTS 
# playing speech
from playsound import playsound
# transcribe audio
import whisper

import sounddevice as sd
from scipy.io.wavfile import write
import warnings

warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

def record_audio(seconds):
    print("recording...")
    fs = 44100  # Sample rate

    recording = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
    sd.wait()  # Wait until recording is finished
    write('input.wav', fs, recording)  # Save as WAV file
    print("finished recording")
    return

def audio_to_text(audio_file, model="base"):
    model = whisper.load_model(model)
    return model.transcribe("input.wav")['text']

def text_to_speech(message: str, language = "es"):
    speech = gTTS(text=message, lang=language)
    speech.save('output.mp3')
    playsound('output.mp3')

def main():
    input_text = input("Enter text to translate from Spanish to English: ")
    text_to_speech(input_text)
    translated = _get_translation(input_text)
    print(f"translated: {translated}\n")
    # input_text = None
    # seconds = None
    # choice = input("Enter 1 to record or 2 to type: ")
    # try:
    #     choice = int(choice)
    #     if choice == 1:
    #         seconds = int(input("Enter number of seconds to record: "))
    #     elif choice == 2:
    #         input_text = input("Enter text: ")
    #     else:
    #         print("Invalid choice")
    #         return
    # except:
    #     print("must be either 1 or 2")
    #     return
    # if seconds:
    #     record_audio(seconds)
    #     scanned_text = audio_to_text("input.wav")
    #     print(f"Scanned text: {scanned_text}") 
    #     scanned_text = correct_text(scanned_text)
    #     text_to_speech(scanned_text)
    #     translated = _get_translation(scanned_text)
    #     print(f"translated: {translated}\n\n") 
    # if input_text:
    #     text_to_speech(input_text)
    #     translated = _get_translation(input_text)
    #     print(f"translated: {translated}\n\n")


def correct_text(scanned_text):
    answer = input("Is the text correct? (y/n)")
    if answer == "y":
        return scanned_text
    else:
        return input("Enter corrected text: ")

def _get_translation(scanned_text: str):
    response = requests.post(url="https://api-free.deepl.com/v2/translate", 
    headers={'Authorization': 'DeepL-Auth-Key ' + DEEPL_ACCESS_KEY}, \
    data={"text": [f"{scanned_text}"],
     "target_lang": "EN",
     "source_lang":"ES"
     }
    )
    if response.status_code == 200:
        return str(response.json()["translations"][0]["text"]).replace("\n", " ")
    else:
        print(f"Error requesting URL: {url}\n{response.status_code}:\n{response.reason}")
        return None


if __name__=="__main__":
    while(True):
        time.sleep(1)
        main()

        

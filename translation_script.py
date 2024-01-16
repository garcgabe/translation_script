from env import DEEPL_ACCESS_KEY
import requests
import time, os

# text to speech
from gtts import gTTS 
# playing speech
from playsound import playsound
# transcribe audio
import whisper

import sounddevice as sd
from scipy.io.wavfile import write


def record_audio(seconds):
    print("recording...")
    fs = 44100  # Sample rate

    recording = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
    sd.wait()  # Wait until recording is finished
    write('input.wav', fs, recording)  # Save as WAV file
    print("finished recording")
    return

 
# Whisper performs speech-to-text
# give it output.wav
def audio_to_text(audio_file, model="tiny"):
    model = whisper.load_model(model)
    return model.transcribe("input.wav")['text']

def text_to_speech(message: str, language = "es"):
    speech = gTTS(text=message, lang=language)
    speech.save('output.mp3')
    playsound('output.mp3')

def main(filepath, start_time):
    seconds = input("Enter number of seconds to record:")
    try:
        seconds = int(seconds)
    except:
        print("Seconds must be an integer")
        return
    if seconds > 2 and seconds < 15:
        record_audio(seconds)
        scanned_text = audio_to_text("input.wav")
        print(f"Scanned text: {scanned_text}") 
        scanned_text = correct_text(scanned_text)
        text_to_speech(scanned_text)
        translated = _get_translation(scanned_text)
        print(f"translated: {translated}\n\n") 

    return time.time()

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
    session_start_time = time.time()
    print(f"Session start time: {session_start_time}")
    filepath = "/Users/garcgabe/Desktop/"

    while(True):
        time.sleep(3)
        session_start_time = main(filepath, session_start_time)

        
from env import DEEPL_ACCESS_KEY, OPENAI_API_KEY
import requests
import os, time, sys 

# text to speech
from gtts import gTTS 
# playing speech
from playsound import playsound
# transcribe audio
import whisper
# AI tool
from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

import sounddevice as sd
from scipy.io.wavfile import write
import warnings
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

import spacy

SYSTEM_PROMPT = """
    You are a succinct and effective spanish teacher for someone who speaks english. \
    They are translating spanish sentences to english, and are curious about actual definitions of \
    spanish words, as well as the conjugations of verbs. point out any important grammatical differences \
    or similarities between the spanish sentence and the english translation. the goal here is to fully \
    understand how the spanish was converted to english, and also to take apart the spanish sentence formation. \
    You should always answer in English unless asked for Spanish, and you should answer the last user message sent. 
"""

# # Load the Spanish NLP model
# nlp = spacy.load("es_core_news_sm")

# # Function to analyze the sentence
# def analyze_sentence(sentence):
#     doc = nlp(sentence)
#     for token in doc:
#         print(token)
#         print(f"Word: {token.text}, Lemma: {token.lemma_}, POS: {token.pos_}")


def _text_to_speech(message: str, language = "es"):
    speech = gTTS(text=message, lang=language)
    speech.save('output.mp3')
    playsound('output.mp3')

def main():
    print("* * * * * * * * * * * * * * * * * * * * * * * * * * *\n*")
    while True:
        # list of dict objects; each dict is a message with a role and a content
        # ex. [ { "role": "user", "content": "hey there chatGPT!" } ]
        context = [{"role": "system", "content": f"{SYSTEM_PROMPT}"}]
        input_text = input("***   input: ")

        _text_to_speech(input_text)
        translation = _get_translation(input_text)
        print("*\n* * * * * * * * * * * * * * * * * * * * * * * * * * *\n*")
        print(f"***   output: {translation}\n*")

        full_translation_string = f"Please explain how, in English: {input_text} translates to Spanish as: {translation}"
        context.append({"role":"user", "content":full_translation_string})
        translation_explained = _get_question_response(full_translation_string, context) # might wanna make async for performance
        print(f'***   explanation: {translation_explained}\n*')

        # add the translation string and the agent response
        context.append({"role":"assistant", "content": translation_explained})

        response = input("***   enter q&a? (y/*): ")
        if response.lower() == 'y':
            while True: 
                question = input("***   enter question: ")
                if question=='d':
                    print('\n'+elem for elem in context)
                    break
                if len(question) <=5:
                    print("*")
                    print("*")
                    break
                print("***")
                context.append({"role":"user", "content":question})
                answer = _get_question_response(question, context)
                print(f"***   answer: {answer}")

                context.append( {"role":"assistant", "content": answer} )

        else: print("*")

    # def commented_out_audio_part():
    #     input_text = None
    #     seconds = None
    #     choice = input("Enter 1 to record or 2 to type: ")
    #     try:
    #         choice = int(choice)
    #         if choice == 1:
    #             seconds = int(input("Enter number of seconds to record: "))
    #         elif choice == 2:
    #             input_text = input("Enter text: ")
    #         else:
    #             print("Invalid choice")
    #             return
    #     except:
    #         print("must be either 1 or 2")
    #         return
    #     if seconds:
    #         record_audio(seconds)
    #         scanned_text = audio_to_text("input.wav")
    #         print(f"Scanned text: {scanned_text}") 
    #         scanned_text = correct_text(scanned_text)
    #         text_to_speech(scanned_text)
    #         translated = _get_translation(scanned_text)
    #         print(f"translated: {translated}\n\n") 
    #     if input_text:
    #         text_to_speech(input_text)
    #         translated = _get_translation(input_text)
    #         print(f"translated: {translated}\n\n")
    #     def record_audio(seconds):
    #         print("recording...")
    #         fs = 44100  # Sample rate
    #         recording = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
    #         sd.wait()  # Wait until recording is finished
    #         write('input.wav', fs, recording)  # Save as WAV file
    #         print("finished recording")
    #         return

    #     def audio_to_text(audio_file, model="base"):
    #         model = whisper.load_model(model)
    #         return model.transcribe("input.wav")['text']

    #     def correct_text(scanned_text):
    #         answer = input("Is the text correct? (y/n)")
    #         if answer == "y":
    #             return scanned_text
    #         else:
    #             return input("Enter corrected text: ")
    

def _get_translation(scanned_text: str):
    url = "https://api-free.deepl.com/v2/translate"
    response = requests.post(url=url, 
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

def _get_question_response(input: str, context: list[dict] = None):
    completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=context,
    max_tokens=250
    )
    return completion.choices[0].message.content

if __name__=="__main__":
    print("*\n*\n* * *  Spanish to English Translator with DeepL  * * *\n*\n*")
    main()

        

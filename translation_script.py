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

warnings.filterwarnings(
    "ignore", message="FP16 is not supported on CPU; using FP32 instead"
)

SYSTEM_PROMPT = """
Goal
I want a Spanish teaching assistant that helps me understand Spanish sentences by breaking them down\
into their components and explaining the translation process to English.
Return Format
For each Spanish sentence I provide, return:

The complete English translation
A word-by-word breakdown with literal meanings
Explanation of verb conjugations used
Identification of grammatical structures
Notes on any important differences between Spanish and English syntax

Warnings
Be careful to explain actual definitions rather than just translations. Highlight false cognates \
and common misunderstandings. Ensure conjugation explanations are accurate.
--
Context dump
For context: I'm an English speaker learning Spanish. I've studied some basics but struggle \
with understanding how Spanish sentences are constructed. I want to fully understand the \
mechanics behind translations rather than just memorizing phrases. I'm particularly interested \
in verb conjugations and grammatical differences between the languages. I learn best when I can see \
exactly how each part of a sentence functions. Please always answer in English unless I specifically \
request Spanish examples.
"""


# def _text_to_speech(message: str, language="es"):
#     speech = gTTS(text=message, lang=language)
#     speech.save('output.mp3')
#     playsound('output.mp3')


def main():
    print("* * * * * * * * * * * * * * * * * * * * * * * * * * *\n*")
    while True:
        # list of dict objects; each dict is a message with a role and a content
        # ex. [ { "role": "user", "content": "hey there chatGPT!" } ]
        context = [{"role": "system", "content": f"{SYSTEM_PROMPT}"}]
        input_text = input("***   input: ")

        # _text_to_speech(input_text)
        translation = _get_translation(input_text)
        print("*\n* * * * * * * * * * * * * * * * * * * * * * * * * * *\n*")
        print(f"***   output: {translation}\n*")

        full_translation_string = f"Please explain how, in English: {input_text} translates to Spanish as: {translation}"
        context.append({"role": "user", "content": full_translation_string})
        translation_explained = _get_question_response(context)
        print(f'***   explanation: {translation_explained}\n*')

        # add the translation string and the agent response
        context.append({"role": "assistant", "content": translation_explained})

        response = input("***   enter q&a? (y/*): ")
        if response.lower() == 'y':
            while True:
                question = input("***   enter question: ")
                if question == 'd':
                    print('\n' + elem for elem in context)
                    break
                if len(question) <= 5:
                    print("*\n*")
                    break
                print("***")
                context.append({"role": "user", "content": question})
                answer = _get_question_response(context)
                print(f"***   answer: {answer}")

                context.append({"role": "assistant", "content": answer})

        else:
            print("*")


def _get_translation(scanned_text: str):
    url = "https://api-free.deepl.com/v2/translate"
    response = requests.post(
        url=url,
        headers={'Authorization': 'DeepL-Auth-Key ' + DEEPL_ACCESS_KEY},
        data={"text": [f"{scanned_text}"], "target_lang": "EN", "source_lang": "ES"},
        timeout=30,
    )
    if response.status_code == 200:
        return str(response.json()["translations"][0]["text"]).replace("\n", " ")
    else:
        print(
            f"Error requesting URL: {url}\n{response.status_code}:\n{response.reason}"
        )
        return None


def _get_question_response(context: list[dict] = None):
    completion = client.chat.completions.create(
        model="gpt-4o-mini", messages=context, max_tokens=250
    )
    return completion.choices[0].message.content


if __name__ == "__main__":
    print("*\n*\n* * *  Spanish to English Translator with DeepL  * * *\n*\n*")
    main()

import pytesseract
from PIL import Image
from env import DEEPL_ACCESS_KEY
import requests

import time, os
from bs4 import BeautifulSoup

#def ex():
    #response = requests.get(url)
    # if response.status_code == 200:
    #     html = BeautifulSoup(response.content, 'html.parser')
    #     ex = html.find_all(re.compile(""))
    # else:
    #     print(f"Error requesting URL: {url}\n{response.status_code}:\n{response.reason}")

def main(filepath, start_time):
    new_file = None
    files = os.listdir(filepath)
    for file in files:
        file_stats = os.stat(filepath+file)
        if file_stats.st_mtime > start_time and "DS_Store" not in file:
            #print(f"File: {file}, last mod: {file_stats.st_mtime}")
            new_file = file

    if new_file:
        scanned_text = pytesseract.image_to_string(Image.open(filepath+new_file))
        print(scanned_text.replace("\n", " "))
        _get_translation(scanned_text)

    return time.time()
def _get_translation(scanned_text):
    response = requests.post(url="https://api-free.deepl.com/v2/translate", 
    headers={'Authorization': 'DeepL-Auth-Key ' + DEEPL_ACCESS_KEY}, \
    data={"text": [f"{scanned_text}"],
     "target_lang": "EN",
     "source_lang":"ES"
     }
    )
    if response.status_code == 200:
        print(str(response.json()["translations"][0]["text"]).replace("\n", " "))
        print("\n")
    else:
        print(f"Error requesting URL: {url}\n{response.status_code}:\n{response.reason}")


if __name__=="__main__":
    session_start_time = time.time()
    print(f"Session start time: {session_start_time}")
    filepath = "/Users/garcgabe/Desktop/"

    while(True):
        time.sleep(3)
        session_start_time = main(filepath, session_start_time)

        
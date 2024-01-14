import translate

import sys, os
from bs4 import BeautifulSoup


def translate(url):
    response = requests.get(url)

    if response.status_code == 200:
        html = BeautifulSoup(response.content, 'html.parser')
        ex = html.find(re.compile(">2022-02-07 14:03</td>"))
    else:
        print(f"Error requesting URL: {url}\n{response.status_code}:\n{response.reason}")


if __name__=="__main__":
    print("please enter the URL of the article you want to translate")
    url = input()
    translate(url)
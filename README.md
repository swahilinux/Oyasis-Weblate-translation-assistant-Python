# Oyasis-Weblate-translation-assistant-Python

A python module for connecting to your weblate project to enable translation without using a browser. Can be intergrated with bots and web apps. 

Built with ❤️ by [Oyamoh Brian](https://github.com/oyamoh-brian) for [Swahilinux](https://swahilinux.org)

## Installation

To install:

`pip install -r requirements.txt`

## Running

1. Make appropriate configurations in `config.ini` file
3. Run `python main.py`

## To-do

1. Build bots (telegram, facebook) to leverage project functionality, to better improve crowd translation

We welcome comments and suggestions for improvement 😊

=======

A python tool/module for connecting to your weblate projects to enable translation without using a browser. Can be intergrated with bots and web apps


Make sure you have the following python modules in your environment 

**requests, lxml,bs4, re, random**


Here is a usage sample


```python
from Oyasis import oyasis
#configure your login
#input the correct credentials
config = oyasis.Ini(username="username",password="password#")
#acquire new session using the config deta
session = oyasis.Session(ini=config)
#start translation
tafsiriWork = oyasis.Tafsiri(session=session)
#selecting a project to work on
#tafsiriWork.selectProject("Mate User Guide")
tafsiriWork.selectRandomProject()
#select random string
while(True):
    randomString=tafsiriWork.getRandomString()
    print(randomString["RandString"])
    translated = input("Translation: ")
    tafsiriWork.translate(translation=translated,todo=randomString)
```


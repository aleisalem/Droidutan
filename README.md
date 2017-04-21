# Droidutan
Droidutan (Android + Orangutan) is a simple Python API built to test Android apps. The API is built on top of AndroidViewClient (https://github.com/dtmilano/AndroidViewClient). The testing methodology of Droidutan attempts to emulate the interaction between a user and the app under test. That is to say, unlike monkey-based tools, Droidutan does not randomly flood the app with events; it rather starts the main activity of an app, retrieves the UI elements of such activity, and interacts with the retrieved elements one at a time. The API also broadcasts intents to the app and perform actions like swiping, touching random coordinates, et cetera.

Droidutan automatically restarts the main activity of an app in case of a crash. That said, the API is not designed to unveil bugs within the app. It is built to automatically interact with Android apps, whilst a hooking tool is monitoring the app's interaction with the system for malware analysis and detection purposes. That does NOT prevent Droidutan from revealing bugs and/or unhandled scenarios within the app, though ;)

## Dependencies
Droidutan depends on the existence of the following tools:
* Androguard is used for statically analyzing the target APK and extracting information about its components (https://github.com/androguard/androguard)
* AndroidViewClient by Diego Torres Milano (https://github.com/dtmilano/AndroidViewClient)

## Installation
The API can be installed as follows:
1. Download or clone the repo (git clone https://github.com/aleisalem/Droidutan)
2. Navigate to the main directory (cd Droidutan)
3. Run setup script (with root privileges) e.g. (sudo python setup.py install)

## Usage
To test an APK, simply import Droidutan and use the "testApp" method. The code is quite easy to follow, and is decently documented, I reckon. :)


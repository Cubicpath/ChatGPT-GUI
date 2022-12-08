ChatGPT-GUI
===============
An unofficial GUI app for ChatGPT.

------------------------------

[![MIT License](https://img.shields.io/github/license/Cubicpath/ChatGPT-GUI?style=for-the-badge)][license]

[![PyPI](https://img.shields.io/pypi/v/chatgpt-gui?label=PyPI&logo=pypi&style=flat-square)][homepage]
[![Python](https://img.shields.io/pypi/pyversions/chatgpt-gui?label=Python&logo=python&style=flat-square)][python]
[![CPython](https://img.shields.io/pypi/implementation/chatgpt-gui?label=Impl&logo=python&style=flat-square)][python]

------------------------------

**Note: This project is in a public alpha, and as such, many features are not complete.**

### Other Documents:
- [Changelog][changelog_github]
- [License][license_github]

### Table of Contents
- [About](#about)
     - [Features](#features)
- [How to Use](#how-to-use)
     - [Installation](#installation)
     - [Authentication](#authentication)
     - [Themes](#themes)
          - [Theme File Structure](#theme-file-structure)


### Disclaimer:
_**ChatGPT-GUI is in no way associated with, endorsed by, or otherwise affiliated with OpenAI.**_

About:
---------------
ChatGPT-GUI is an application written using [Qt for Python][PySide] that allows you to
easily talk to Assistant, the AI based on [ChatGPT].

This project is a fork of my other project, [HaloInfiniteGetter](https://github.com/Cubicpath/HaloInfiniteGetter).

If you like this application, be sure to star :)

### Features:
- [x] Email/Password Login to [ChatGPT] Without Browser
  - (Captcha solving is untested but implemented)
- [x] Bypasses Moderation
- [x] Desktop & Start Menu Shorcuts
- [x] Session (token) Persistence
- [x] Automatic Access Token Refreshing
- [x] Multiple Concurrent Conversations
- [x] Multi-line input
- [x] Exception Reporter & Traceback Viewer
- [x] Themes
  - Builtin themes are: [Breeze Dark, Breeze Light, and Legacy]

#### Todo:
- [ ] Conversation Saving & Loading
- [ ] Pretty Conversation Views
- [ ] Proxy Settings

How to Use:
---------------

### Installation:
- First, install Python 3.10 using [this link][python310]
- Then, open command prompt (Win + R -- type in "cmd") and type `pip install chatgpt-gui`
  - Optionally, to install the latest unstable version, type `pip install git+https://github.com/Cubicpath/ChatGPT-GUI.git`
- And you are done! To launch the program simply type `chatgpt`
  - Once launched, you can create a desktop shortcut by using the `Create Desktop Shortcut` tool
under the `Tools` context menu

### Authentication:
Thanks to [PyChatGPT] and [tls-client][python-tls-client], there exists a method to authenticate without
messing around with tokens or the browser. Simply sign in from the app itself!.

![Sign In](https://i.imgur.com/DabSYBhl.png)

If you want to use session tokens anyway, here is the guide:
- Sign in to [ChatGPT] on your browser
- Navigate to the Cookies for chat.openai.com
  - On Firefox -- F12 > Move to the "Storage" tab > Under "Cookies" select https://chat.openai.com
- Double-click the `__Secure-next-auth.session-token` cookie value and copy with CTRL + C
- Open the Settings window, unlock the input by pressing the "Edit Session Token" button, then paste the copied value.
- Press the Set button, and you should now be authenticated!

### Themes:
Themes are a way to style already-existing elements (Think CSS). They are held in a directory with their resources
and stylesheet in the same folder level.

#### Theme File Structure:
    ../
    │
    ├───[theme_id]/
    │       ├─── [icon1_name].svg
    │       ├─── [icon2_name].svg
    │       ├─── [icon3_name].svg
    │       └─── stylesheet.qss
    │

The current builtin themes are:
- `Breeze Dark`
- `Breeze Light`
- `Legacy (Default Qt)`

While the current breeze themes are slightly modified versions, you can view the original themes at [BreezeStyleSheets].

[BreezeStyleSheets]: https://github.com/Alexhuszagh/BreezeStyleSheets "BreezeStyleSheets"
[changelog_github]: https://github.com/Cubicpath/ChatGPT-GUI/blob/master/CHANGELOG.md "Changelog"
[ChatGPT]: https://https://chat.openai.com "ChatGPT"
[homepage]: https://pypi.org/project/chatgpt-gui/ "ChatGPT-GUI PyPI"
[license]: https://choosealicense.com/licenses/mit "MIT License"
[license_github]: https://github.com/Cubicpath/ChatGPT-GUI/blob/master/LICENSE "MIT License"
[PySide]: https://pypi.org/project/PySide6/ "PySide6"
[python]: https://www.python.org "Python"
[python310]: https://www.python.org/downloads/release/python-3100/ "Python 3.10"
[PyChatGPT]: https://github.com/FlorianREGAZ/Python-Tls-Client "PyChatGPT"
[python-tls-client]: https://github.com/FlorianREGAZ/Python-Tls-Client "tls-client"

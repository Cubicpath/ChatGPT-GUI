ChatGPT-GUI
===============

[![MIT License](https://img.shields.io/github/license/Cubicpath/ChatGPT-GUI?style=flat-square)][license]
[![PyPI](https://img.shields.io/pypi/v/chatgpt-gui?label=PyPI&logo=pypi&style=flat-square)][homepage]
[![Python](https://img.shields.io/pypi/pyversions/chatgpt-gui?label=Python&logo=python&style=flat-square)][python]
[![CPython](https://img.shields.io/pypi/implementation/chatgpt-gui?label=Impl&logo=python&style=flat-square)][python]

------------------------------

An unofficial GUI app for ChatGPT.

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
          - [Session Token Guide](#session-token-guide)
          - [Session Data](#session-data)
     - [Saving/Loading Conversations](#savingloading-conversations)
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
- ~~[x] Email/Password Login to [ChatGPT] Without Browser~~
  - ~~(Captcha solving is untested but implemented)~~
- [x] Proxy Settings
  - Supported Protocols are `HTTP` and `SOCKS5`
- [x] Executable Script in PATH (`chatgpt`)
- [x] Desktop & Start Menu Shorcuts
- [x] Session (token) Persistence
- [x] Automatic Access Token Refreshing
- [x] Multiple Concurrent Conversations
- [x] Conversation Saving & Loading
- [x] Multi-line input
- [x] Exception Reporter & Traceback Viewer
- [x] Themes
  - Builtin themes are: [Breeze Dark, Breeze Light, and Legacy]

#### Todo:
- [ ] Pretty Conversation Views
- [ ] Retry AI Message

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
~~Thanks to [rawandahmad698] and [tls-client][python-tls-client], there exists a method to authenticate without
messing around with tokens or the browser. Simply sign in from the app itself!.~~

**Google Chrome is currently required to automatically bypass cloudflare.**

Email & Password login is currently not working.
Refer to session token authentication in the meantime.

![Sign In](https://i.imgur.com/DabSYBhl.png)

#### Session Token Guide:
- Sign in to [ChatGPT] on your browser
- Navigate to the Cookies for chat.openai.com
  - On Firefox -- F12 > Move to the "Storage" tab > Under "Cookies" select https://chat.openai.com
- Double-click the `__Secure-next-auth.session-token` cookie value and copy with CTRL + C
- Open the Settings window, unlock the input by pressing the "Edit Session Token" button, then paste the copied value.
- Press the Set button, and you should now be authenticated!

#### Session Data:
Session data is stored in a hidden file (`~/.config/chatgpt_gui/.session.json`), for persistence.
When you sign out or clear your session token, it automatically deletes all session data.

If you ever need to directly edit your session data, it follows the following format:
```json
{
  "user": {
    "id": "Your user id (starting with a 'user-' prefix)",
    "name": "Your username (usually same as your email)",
    "email": "The email tied to your session",
    "image": "Link to your profiles image (usually same as your picture)",
    "picture": "Link to your profile picture",
    "groups": [],
    "features": []
  },
  "cloudflare": {
    "bm": "Value of the __cf_bm cookie",
    "clearance": "Value of the cf_clearance cookie",
    "expires": "1h from the time cf_clearance is acquired"
  },
  "expires": "Automatically acquired after refresh_auth()",
  "token": "Value of the __Secure-next-auth.session-token cookie",
  "user_agent": "User Agent the Client/Authenticator use"
}
```

### Saving/Loading Conversations
You can save your currently selected conversation with ChatGPT by right-clicking any tab and
pressing the `Export Conversation To...` button. This will open a file dialog where you can rename
your conversation anything, which will show when loaded.

You can load a conversation that was previously saved by pressing the `Import Conversation From...`
button, and selecting the JSON file containing the conversation.

By default, all conversations are stored in the `~/.cache/chatgpt_gui/` directory.
But you can choose any folder when exporting.

**NOTE: Conversations from one account CANNOT be accessed from another.**

#### Conversation Format:
Conversations are stored as a linear list of messages, where each message is
a response to the one before it. All UUID's are tracked, which allows the Client to
continue conversations after import.

They are stored in the following data format:
```json
{
  "id": "Conversation UUID",
  "messages": [
    {
      "id": "Message UUID",
      "role": "user",
      "content": {
        "content_type": "text",
        "parts": [
          "Your message to ChatGPT"
        ]
      }
    },
    {
      "id": "Message UUID",
      "role": "assistant",
      "content": {
        "content_type": "text",
        "parts": [
          "Response from ChatGPT"
        ]
      }
    }
  ]
}
```

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
[rawandahmad698]: https://github.com/rawandahmad698 "rawandahmad698"
[python-tls-client]: https://github.com/FlorianREGAZ/Python-Tls-Client "tls-client"

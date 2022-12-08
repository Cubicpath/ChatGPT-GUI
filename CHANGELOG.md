# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.3.1] - 2022-12-7 [PyPI](https://pypi.org/project/chatgpt-gui/0.3.1)
### Added
- Shows current account pfp and email address
- "Solve Captcha" dialog (Untested)

### Changed
- Default message action from `next` to `variant`

### Fixes
- Crash on startup


## [0.3] - 2022-12-7 [PyPI](https://pypi.org/project/chatgpt-gui/0.3)
### Added
- Authenticator (No more manual session tokens)
- Sign In / Sign Out
- `tls-client` and `beautifulsoup4` hard-requirements

### Changed
- session token storage format (`.session` to `.session.json`)
    - This is backwards-compatible and will automatically be migrated.


## [0.2] - 2022-12-6 [PyPI](https://pypi.org/project/chatgpt-gui/0.2)
### Added
- Conversation tabs
- Multi-line inputs

### Changed
- Scroll to bottom of output when a message is appended

### Fixes
- Shortcut icon


## [0.1.1] - 2022-12-4 [PyPI](https://pypi.org/project/chatgpt-gui/0.1.1)
### Fixes
- Broken Icons
- [gh-1](https://github.com/Cubicpath/ChatGPT-GUI/issues/1)


## [0.1] - 2022-12-4 [PyPI](https://pypi.org/project/chatgpt-gui/0.1)
### Added
- GUI from HaloInfiniteGetter
- Session token client
- Basic input and output communication to ChatGPT


[Unreleased]: https://github.com/Cubicpath/ChatGPT-GUI/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/Cubicpath/ChatGPT-GUI/compare/v0.3...v0.3.1
[0.3]: https://github.com/Cubicpath/ChatGPT-GUI/compare/v0.2...v0.3
[0.2]: https://github.com/Cubicpath/ChatGPT-GUI/compare/v0.1.1...v0.2
[0.1.1]: https://github.com/Cubicpath/ChatGPT-GUI/compare/v0.1.0...v0.1.1
[0.1]: https://github.com/Cubicpath/ChatGPT-GUI/releases/tag/v0.1

# discord-koe

Python 3.9.16 (PyPy 7.3.11) 에서 실행되도록 구현한 Discord용 TTS 봇입니다.

*.python-version* 파일에 정의된 `discord-koe`는 아래와 같이 생성되었습니다.

```sh
pyenv virtualenv pypy3.9-7.3.11 discord-koe
```

실행하려면 아래 네 개의 환경 변수가 필요합니다.

- *DISCORD_TOKEN*: 디스코드에서 작동할 봇의 토큰
- *GOOGLE_API_KEY*: 입력받은 문자열의 언어를 판단하기 위해 사용될, Google Translate 접근 권한이 있는 API 키
- *VOM_EMAIL*: [VoiceOverMaker] API를 사용할 계정의 이메일
- *VOM_PASSWORD*: [VoiceOverMaker] API를 사용할 계정의 암호

봇은 메시지 보기, 메시지 쓰기, 음성 채널에서 말하기, 음성 채널 멤버 보기 권한이 필요합니다. 메시지 쓰기와 음성 채널 멤버 보기는 필수는 아니지만 없으면 불편합니다.

사용자는 음성 채널에 참여한 채로 `,,` 로 시작하는 메시지를 음성 채널에 부속된 텍스트 채널에서 말함으로서 봇에게 음성으로 말하도록 시킬 수 있습니다.

말하기를 제외한 모든 명령어는 봇을 호출하는 것으로 사용할 수 있습니다.

사용자가 음성 채널에 참여하지 않은 경우, 봇은 말하기를 포함한 모든 명령어를 무시할 것입니다.

[VoiceOverMaker]: https://voiceovermaker.io

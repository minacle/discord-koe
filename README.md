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


## FAQ

### `,,` 없이 말하고 싶어요.

다음과 같은 명령어를 통해 Koe가 음성채팅방의 텍스트 채팅 내용을 기본적으로 읽어줍니다.

```Text
@Koe enable
```

```Text
@Koe on 
```

```Text
@Koe 1
```

### 목소리 및 성별을 바꾸고 싶어요.

성별을 여성으로 바꾸기 위해선 다음 명령어로 바꿀 수 있습니다.

```Text
@Koe gender female
```

목소리 목록은 다음 명령어로 확인할 수 있습니다.

```Text
@Koe voices ko 1
```

```Text
@Koe voices ko 2
```

목소리 견본은 다음 홈페이지에서 들어볼 수 있습니다.

https://voiceovermaker.io/#languages

목소리는 다음 명령어로 설정할 수 있습니다.

```Text
@Koe voice ko 3
```

```Text
@Koe voice ko JiMin
```
---
성별을 남성으로 바꾸기 위해선 다음 명령어로 바꿀 수 있습니다.

```Text
@Koe gender male
```

목소리 목록은 다음 명령어로 확인할 수 있습니다.

```Text
@Koe voices ko 1
```

```Text
@Koe voices ko 2
```
목소리 견본은 다음 홈페이지에서 들어볼 수 있습니다.

https://voiceovermaker.io/#languages

목소리는 다음 명령어로 설정할 수 있습니다.

```Text
@Koe voice ko 3
```

**해당 명령어는 목소리 목록을 보는 명령어와 달리 복수형이 아닙니다. (voice)**

### 언어코드가 뭔가요?

Koe는 다국어를 지원하기 때문에 언어별 목소리 설정이 가능합니다. 기본적으로 한국어 사용자는 언어코드를 ko와 ko-KR 로 설정할 수 있습니다.

언어코드는 ISO 639-1와 ISO 3166-1를 따릅니다.
Koe 에서 주요 언어에 대한 언어코드는 다음과 같습니다.

**목소리 목록을 부를 때는 ISO 639-1과 ISO 3166-1 을 사용할 수 있으나 목소리를 설정은 구글 번역기 API에서 지원하는 언어코드를 사용해야합니다. (주로 ISO 639-1 를 따릅니다.)**

- **한국어**:
   - `ko` _(ISO-639-1)_
   - `ko-KR` _(ISO 3166-1)_

- **영어**:
  - `en` _(ISO 639-1)_

- **영어는 주요 사용국이 많은 언어로 좀 더 자세히 나라를 설정할 수도 있습니다.**:
  - `en-GB` _(ISO 3166-1) (영국 억양 영어)_

  - `en-US` _(ISO 3166-1) (미국 억양 언어)_

- **일본어**:
  - `ja` _(ISO 639-1)_
  - `ja-JP` _(ISO 3166-1)_

- **중국어**:
  - `yue` _(ISO 639-1)_
  - `yue-CN` _(ISO 3166-1)_
  - `zh` _(구글 번역기 API 언어코드, voices 설정에 필요)_
  - `zh-CN` _(구글 번역기 API 언어코드, voices 설정에 필요)_

### KOE가 말하는 걸 중간에 중지하고 싶어요.

누군가 Koe로 테러했을 때 혹은 누군가 Koe를 이용하였는데 무언정지 상태가 되어 중지하고 싶을 때 사용하는 명령어입니다.

```Text
@Koe stop
```

```Text
@Koe .
```

### Koe가 고장났어요.

#### 셀프호스트인 경우

```Text
@Koe stop
```

명령어를 통해 일단 Koe를 중지시킵니다.

```Text
@Koe ping
```

명령어를 통해 Koe와의 통신상태를 확인합니다.

```Text
@Koe q?
```

```Text
@Koe queue
```

명령어를 통해 큐 상태를 점검합니다.
큐 상태가 꼬이면 superuser가 relase-vom-lock, relase-speak-lock 명령어를 통해 큐에 lock을 해제처리합니다. (release 합니다.)

```Text
@Koe q!
```

```Text
@Koe quit
```

를 통해 Koe 봇을 내보냈다가 다시 채팅을 쳐서 들여보냅니다.

다 안 되면 @Koe 데몬을 재시작합니다.

#### 사용자의 경우

셀프호스트의 절차 중 Koe 데몬을 재시작하기 전까지 수행합니다.

### superuser는 어떻게 설정하나요?

Koe 데몬을 실행시키고 설정값을 변경하면 (EX voice or gender 등) config.yaml이 생성됩니다.

config.yaml 에서 관리자 사용자 ID 밑에 superuser: true 를 추가합니다.

```yaml
123456789012345678:
  superuser: true
  gender: female
  voice:
    ko: Korean (ko-KR, Female, Neural) - JiMin
```

**디스코드 사용자 ID는 디스코드에서 개발자모드를 설정한 뒤 프로필에서 우클릭으로 사용자 ID를 복사하여 확인할 수 있습니다.**

### alias 가 뭔가요?

alias 는 특정 단어를 다르게 읽어줍니다.

EX) ㄱㄱ 을 고고 로 읽음

기본적으로 galiases.yaml 파일 명세를 따르며 사용자가 다음과 같은 명령어를 통해 추가적으로 설정할 수 있습니다.

```Text
alias ko 트위터 똥
```

다음과 같은 명령어로 alias 설정을 볼 수 있습니다.

```Text
@Koe alias ko 트위터
```

성공하면 다음과 같이 반환합니다.

```Text
    >alias ko 트위터
    >>똥
```

기본적인 명령어 명세는 다음과 같습니다.

```Text
a[lias]|a! [force] <LANGUAGE|~> <REGEX> [ALIAS]
```

### 설정 데이터는 어떻게 저장되나요?

설정 데이터들은 루트 디렉토리에 yaml 파일로 저장되며 그종류에 따라 config.yaml, enabled.yaml, aliases.yaml 로 나뉘어 저장됩니다.
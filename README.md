# discord-koe

Python 3.9.18 (PyPy 7.3.15) 에서 실행되도록 구현한 Discord용 TTS 봇입니다.

*.python-version* 파일에 정의된 `discord-koe`는 아래와 같이 생성되었습니다.

```sh
pyenv virtualenv pypy3.9-7.3.15 discord-koe
```

실행하려면 아래 네 개의 환경 변수가 필요합니다.

- `DISCORD_TOKEN`: 디스코드에서 작동할 봇의 토큰
- `GOOGLE_API_KEY`: 입력받은 문자열의 언어를 판단하기 위해 사용될, Google Translate 접근 권한이 있는 API 키
- `VOM_EMAIL`: [VoiceOverMaker] API를 사용할 계정의 이메일
- `VOM_PASSWORD`: [VoiceOverMaker] API를 사용할 계정의 암호

봇은 메시지 보기, 메시지 쓰기, 음성 채널에서 말하기, 음성 채널 멤버 보기 권한이 필요합니다. 메시지 쓰기와 음성 채널 멤버 보기는 필수는 아니지만 없으면 불편합니다.

사용자는 음성 채널에 참여한 채로 `,,`로 시작하는 메시지를 음성 채널에 부속된 텍스트 채널에서 말함으로서 봇에게 음성으로 말하도록 시킬 수 있습니다.

봇은 `\,,`로 시작하는 메시지를 절대 말하지 않습니다. 이 동작은 모든 메시지 말하기를 활성화한 사용자의 메시지에도 적용됩니다.

말하기를 제외한 모든 명령어는 봇을 호출하는 것으로 사용할 수 있습니다. 모든 명령어를 보려면 봇을 호출합니다.

봇 관리자는 _config.yaml_ 파일에서 자신의 Discord 사용자 ID에 해당하는 레코드의 `superuser` 키에 `true`를 설정해야 합니다. 이렇게 하면 봇 관리자는 디버그를 위한 명령어를 사용할 수 있습니다. 모든 디버그 명령어를 보려면 봇 관리자가 봇을 호출합니다.

사용자가 음성 채널에 참여하지 않은 경우, 봇은 말하기를 포함한 모든 명령어를 무시할 것입니다. 이 동작은 봇 관리자에게도 적용됩니다.


[VoiceOverMaker]: https://voiceovermaker.io


## FAQ

본 섹션에서는 discord-koe 봇에 대한 자주 묻는 질문과 그에 대한 답변을 제공합니다. 명령어 예시에서 봇의 호출을 `@Koe`로 표시합니다.

### `,,` 없이 말하고 싶어요.

다음 명령어를 입력하여 사용자가 음성 채널에 부속된 텍스트 채널에 입력한 모든 메시지를 음성으로 말하도록 설정할 수 있습니다.

```text
@Koe enable
```

```text
@Koe on
```

```text
@Koe 1
```

위 명령어는 모두 같은 동작을 하며, `help`에서 다음과 같이 설명됩니다.

> `enable`|`on`|`1`

### 기본 성별을 지정하고 싶어요.

다음 명령어를 입력하여 기본 성별을 지정할 수 있습니다.

```text
@Koe gender female
```

```text
@Koe g f
```

위 명령어는 모두 같은 동작을 하며, 기본 성별을 여성으로 지정합니다.

```text
@Koe gender male
```

```text
@Koe g m
```

위 명령어는 모두 같은 동작을 하며, 기본 성별을 남성으로 지정합니다.

해당 명령어는 `help`에서 다음과 같이 설명됩니다.

> `g`[`ender`]  [`f`[`emale`]|`m`[`ale`]|`?`]

### 목소리를 지정하고 싶어요.

#### 목소리 목록을 확인하기

다음과 같은 명령어를 입력하여 목소리 목록을 확인할 수 있습니다.

```text
@Koe voices ko
```

```text
@Koe v? ko 2
```

위 명령어는 각각 한국어 목소리 목록의 첫 번째 페이지와 두 번째 페이지를 보여줍니다.

해당 명령어는 `help`에서 다음과 같이 설명됩니다.

> `voices`|`v?`  <*LOCALE*>  [*PAGE_NUMBER*]

> [!IMPORTANT]
> `voice`(`v`) 명령어와 헷갈리지 않도록 주의하세요. `voice`(`v`) 명령어는 목소리를 지정할 때 사용하며, `voices`(`v?`) 명령어는 목소리 목록을 확인할 때 사용합니다.

> [!NOTE]
> **discord-koe**는 TTS 서비스로 [VoiceOverMaker]를 사용하며, 일부 목소리는 [Languages 섹션](https://voiceovermaker.io/#languages)에서 견본을 들어볼 수 있습니다.

#### 목록에서 확인한 목소리로 지정하기

다음과 같은 명령어를 입력하여 목록에서 확인한 목소리로 지정할 수 있습니다.

```text
@Koe voice ko 3
```

```text
@Koe v ko 14
```

위 명령어는 각각 한국어 목소리 목록에서 세 번째 목소리와 열네 번째 목소리로 지정합니다.

해당 명령어는 `help`에서 다음과 같이 설명됩니다.

> `v`[`oice`]  <*LOCALE*>  [*VOICE_NAME*|*VOICE_INDEX*|`?`]

> [!IMPORTANT]
> `voices`(`v?`) 명령어와 헷갈리지 않도록 주의하세요. `voices`(`v?`) 명령어는 목소리 목록을 확인할 때 사용하며, `voice`(`v`) 명령어는 목소리를 지정할 때 사용합니다.

#### *LOCALE*이란?

**discord-koe**는 다국어를 지원하며, 언어별 목소리를 지정할 수 있습니다. 그렇기 때문에 어느 언어의 목소리 목록을 확인할지, 어느 언어의 목소리를 지정할지에 대해 입력해야 하며, `help`에서는 이를 *LOCALE*이라고 합니다.

*LOCALE*은 ISO 639-1<sup>[[위키백과]](https://ko.wikipedia.org/wiki/ISO_639-1)</sup> 언어 코드이거나, ISO 3166-1<sup>[[위키백과]](https://ko.wikipedia.org/wiki/ISO_3166-1)</sup> 국가 코드를 `-`로 연결한 형식입니다.

눈여겨 볼 점은, **discord-koe**는 메시지를 읽기 전에 먼저 해당 메시지가 어떤 언어로 작성된 것인지 Google 번역에서 제공하는 언어 감지 기능으로 파악하기 때문에, 해당 서비스에서 제공하는 ISO 639-1 언어 코드나, ISO-3166-1 국가 코드를 `-`로 연결한 형식을 사용해야 한다는 것입니다. 전체 언어 코드 목록은 [Google Cloud Translation 가이드 문서의 언어 지원 페이지](https://cloud.google.com/translate/docs/languages?hl=ko)에서 확인할 수 있습니다.

아래는 몇몇 언어의 ISO 639-1 언어 코드나, ISO 3166-1 국가 코드입니다.

- **한국어**:
   - `ko` _(ISO-639-1 언어 코드)_
   - `ko-KR` _(ISO 3166-1 국가 코드를 연결한 형식)_: 대한민국

- **영어**:
  - `en` _(ISO 639-1 언어 코드)_
  - `en-GB` _(ISO 3166-1 국가 코드를 연결한 형식)_: 영국
  - `en-US` _(ISO 3166-1 국가 코드를 연결한 형식)_: 미국

- **일본어**:
  - `ja` _(ISO 639-1 언어 코드)_
  - `ja-JP` _(ISO 3166-1 국가 코드를 연결한 형식)_: 일본

- **중국어**:
  - `zh` _(ISO 639-1 언어 코드)_
  - `zh-CN` _(ISO 3166-1 국가 코드를 연결한 형식)_: 간체
  - `zh-TW` _(ISO 3166-1 국가 코드를 연결한 형식)_: 번체

### 현재 말하기를 중단하고 싶어요.

다음 명령어를 입력하여 의도치 않은 긴 문장 말하기 혹은 올바르게 완료되지 않은 말하기를 중단할 수 있습니다.

```text
@Koe stop
```

```text
@Koe .
```

위 명령어는 모두 같은 동작을 하며, `help`에서 다음과 같이 설명됩니다.

> `stop`|`.`

### 봇이 고장났어요.

현재 말하기가 올바르게 완료되지 않았을 경우 다음 명령어를 입력하여 현재 말하기를 중단하면 해결될 수 있습니다.

```text
@Koe stop
```

봇이 인터넷 연결 문제를 겪고 있는 경우, 다음 명령어를 입력하였을 때 봇이 응답하지 않거나, 매우 높은 지연 시간으로 응답할 수 있습니다.

```text
@Koe ping
```

원격 서비스 혹은 내부 상태에 문제가 있는 경우, 다음 명령어를 입력하여 현재 채널의 메시지에 대한 대기열을 확인할 수 있습니다.

```text
@Koe queue
```

Discord 음성 서버와의 연결 문제를 겪고 있는 경우, 다음 명령어를 입력하여 봇이 강제로 음성 채널에서 나가도록 할 수 있습니다. 이렇게 하면 봇이 다음 말하기를 위해 음성 채널에 다시 들어가게 되며 문제가 해결될 수 있습니다.

```text
@Koe quit
```

어떠한 수단으로도 문제가 해결되지 않는 경우, 봇 관리자는 디버그를 위한 명령어를 사용하여 봇의 상태를 확인하고 문제를 해결하거나, 직접 봇을 재시작해야 합니다.

### 특정 단어를 지정한 발음으로 말하게 하고 싶어요.

> [!NOTE]
> 현재 이 기능은 완전하지 않으며, 향후 업데이트에서 개선될 예정입니다.

`alias` 명령어는 특정 단어를 어떤 발음으로 말할지 지정할 수 있습니다. 아래 예시는 ‘ㄸㅇ’라고 입력하면 ‘따이’라고 발음하게 하는 명령어입니다.

```text
@Koe alias ko ㄸㅇ 따이
```

아래 명령어는 'ㄸㅇ'라는 단어에 대한 발음을 확인합니다.

```text
@Koe alias ko ㄸㅇ
```

'ㄸㅇ'라는 단어에 대한 발음이 더는 필요하지 않다면 아래 명령어로 삭제할 수 있습니다.

```text
@Koe unalias ko ㄸㅇ
```

`alias` 명령어는 `help`에서 다음과 같이 설명됩니다.

> `a`[`lias`]  [`force`]  <*LANGUAGE*|`~`>  <*REGEX*>  [*ALIAS*]

> `a!`  <*LANGUAGE*|`~`>  <*REGEX*>

`unalias` 명령어는 `help`에서 다음과 같이 설명됩니다.

> `unalias`|`~a`  <*LANGUAGE*|`~`>  <*REGEX*>

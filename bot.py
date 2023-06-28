from __future__ import annotations

from auth import Auth
from ld import *
from vom import *

import aiohttp
import asyncio
from contextlib import suppress
from datetime import datetime, timezone
import discord
import discord.ext.tasks
from discord.utils import MISSING
import ffmpeg
from io import StringIO
import logging
import os
from random import Random
import re
from tempfile import mkstemp
from textwrap import dedent
import traceback
import yaml

from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    Type,
    TypeVar,
    Union,
    overload,
)
from typing_extensions import override

if TYPE_CHECKING:
    from _typeshed import StrOrBytesPath


class Bot(discord.Client):

    @override
    def __init__(
        self,
        *args,
        intents: discord.Intents,
        auth: Auth,
        **kwargs
    ) -> None:
        super(Bot, self).__init__(*args, intents=intents, **kwargs)
        self.auth: Auth = auth
        self.ld: LanguageDetector = LanguageDetector(api_key=auth.google.api_key)
        self.vom: VOM
        #
        # {channel_id: [user_id]}
        self.enabled_user_ids_map: dict[int, list[int]] = {}
        self.enabled_user_ids_lock: Optional[asyncio.Lock] = None
        #
        # {user_id: config}
        self.user_config_map: dict[int, dict[str, Any]] = {}
        self.user_config_lock: Optional[asyncio.Lock] = None
        #
        # {channel_id: Event}
        self.speak_end_events_map: dict[int, asyncio.Event] = {}
        self.speak_end_events_lock: Optional[asyncio.Lock] = None
        #
        # [(message, text)]
        self.vom_queue: list[tuple[discord.Message, str]] = []
        self.vom_lock: Optional[asyncio.Lock] = None
        #
        # (message, text)
        self.voming_item: Optional[tuple[discord.Message, str]] = None
        #
        # {channel_id: [(message, text, (opus_file_descriptor, opus_file_name))]}
        self.speak_queue: dict[int, list[tuple[discord.Message, str, tuple[int, str]]]] = {}
        self.speak_lock: dict[int, asyncio.Lock] = {}
        #
        # {channel_id: [(message, text, (opus_file_descriptor, opus_file_name), audio)]}
        self.speaking_queue: dict[int, list[tuple[discord.Message, str, tuple[int, str], discord.FFmpegAudio]]] = {}
        #
        self.is_vom_job_running: bool = False
        #
        # {channel_id: bool}
        self.is_speak_job_running: dict[int, bool] = {}

    @override
    def run(
        self,
        *,
        reconnect: bool = True,
        log_handler: Optional[logging.Handler] = MISSING,
        log_formatter: logging.Formatter = MISSING,
        log_level: int = MISSING,
        root_logger: bool = False,
    ) -> None:
        super(Bot, self).run(
            token=self.auth.discord.token,
            reconnect=reconnect,
            log_handler=log_handler,
            log_formatter=log_formatter,
            log_level=log_level,
            root_logger=root_logger
        )

    def command_or_none(
        self,
        message: discord.Message
    ) -> Optional[str]:
        if message.is_system():
            return None
        if message.author.bot:
            return None
        if self.user.mentioned_in(message):
            if message.content.startswith(f"<@!{self.user.id}>"):
                return message.content[len(f"<@!{self.user.id}>"):].strip()
            elif message.content.startswith(f"<@{self.user.id}>"):
                return message.content[len(f"<@{self.user.id}>"):].strip()
        elif message.role_mentions:
            for role in message.role_mentions:
                if role.is_bot_managed() and self.user in role.members:
                    if message.content.startswith(f"<@&{role.id}>"):
                        return message.content[len(f"<@&{role.id}>"):].strip()
        return None

    def speak_or_none(
        self,
        message: discord.Message
    ) -> Optional[str]:
        if message.is_system():
            return None
        if message.author.bot:
            return None
        if message.mentions or message.role_mentions:
            if re.match(r"^<@[!&]?\d+>", message.content.strip()):
                return None
        if message.reference:
            return None
        if message.content.startswith("\\,,"):
            return None
        if message.author.id in self.enabled_user_ids_map.get(message.channel.id, []):
            return message.clean_content
        elif message.content.startswith(",,"):
            return message.clean_content[2:].strip()
        return None

    async def vom_job(
        self
    ) -> None:
        await self.vom_lock.acquire()
        while self.vom_queue:
            message, text = item = self.vom_queue.pop(0)
            self.voming_item = item
            if not text.strip():
                continue
            self.vom_lock.release()
            print(f"<{message.author}> {text}")
            if not self.vom.voices:
                for _ in range(5):
                    try:
                        await self.vom.list_voices()
                    except:
                        asyncio.sleep(0.5)
                    else:
                        break
            language = "und"
            language_e = []
            for _ in range(3):
                try:
                    language = await self.ld.detect(text)
                except Exception as e:
                    language_e.append(e)
                    print(e)
                else:
                    break
            print(f"Language: {language}")
            voices = self.vom.filter_voices(language)
            print(f"Voices: {len(voices)}")
            if not voices:
                if "-" in language:
                    language = language.split("-")[0]
                    voices = self.vom.filter_voices(language)
                else:
                    starts_with = language + "-"
                    voices = self.vom.filter_voices(starts_with=starts_with)
            if not voices:
                language = "en"
                starts_with = language + "-"
                voices = self.vom.filter_voices(starts_with=starts_with)
            if not voices:
                try:
                    await message.channel.send(f"> ,,{text}\n{None}", reference=message)
                except:
                    pass
                await self.vom_lock.acquire()
                continue
            specified_voice = await self.get_config("voice", language, user=message.author)
            voice = None
            if specified_voice:
                for voice in voices:
                    if voice.language_name == specified_voice:
                        break
                else:
                    voice = None
            if not voice:
                gender = await self.get_config("gender", user=message.author)
                _voices = []
                if gender:
                    for voice in voices:
                        voice_gender = voice.get("ssmlGender", voice.get("Gender", "")).lower()
                        if voice_gender == "female":
                            if gender == "female":
                                _voices.append(voice)
                        elif voice_gender == "male":
                            if gender == "male":
                                _voices.append(voice)
                else:
                    _voices = voices
                if not _voices:
                    _voices = [self.vom.get_default_voice(user=message.author, language="en")]
                if not _voices:
                    if language_e:
                        language_e = "\n".join([str(e) for e in language_e])
                    else:
                        language_e = None
                    try:
                        await message.channel.send(f"> ,,{text}\n{language_e}", reference=message, silent=True)
                    except:
                        pass
                    await self.vom_lock.acquire()
                    continue
                print(f"Voices count: {len(_voices)}")
                random = Random(message.author.id)
                voice = random.choice(_voices)
            print(f"Voice: {voice._source}")
            try:
                ssml = await self.vom.ssml(text, language=language, channel=message.channel)
            except Exception as e:
                print(e)
                traceback.print_exc()
            print(ssml)
            mp3 = None
            mp3_e = []
            for _ in range(2):
                try:
                    mp3 = await self.vom.create_voice(ssml, voice)
                except aiohttp.ClientResponseError as e:
                    print(e)
                    if e.status == 400:
                        break
                    else:
                        mp3_e.append(e.status)
                    if e.status == 401:
                        try:
                            await self.refresh_vom_token(retry=0)
                        except aiohttp.ClientResponseError as e:
                            print(e)
                            mp3_e.append(e.status)
                        except Exception as e:
                            print(e)
                            mp3_e.append(e)
                            traceback.print_exc()
                        else:
                            continue
                except Exception as e:
                    mp3_e.append(e)
                    print(e)
                    traceback.print_exc()
                else:
                    break
            if not mp3:
                if language_e:
                    language_e = "\n".join([str(e) for e in language_e])
                else:
                    language_e = None
                if mp3_e:
                    mp3_e = "\n".join([str(e) for e in mp3_e])
                else:
                    mp3_e = None
                if language_e or mp3_e:
                    with suppress(Exception):
                        await message.channel.send(f"> ,,{text}\n{language_e}\n{mp3_e}", reference=message, silent=True)
                await self.vom_lock.acquire()
                continue
            mp3_file_descriptor, mp3_file_name = mkstemp(suffix=".mp3")
            with os.fdopen(mp3_file_descriptor, "wb", closefd=True) as f:
                f.write(mp3)
            opus_file_descriptor, opus_file_name = mkstemp(suffix=".opus")
            print(f"MP3: {mp3_file_name}")
            print(f"OPUS: {opus_file_name}")
            try:
                stream = ffmpeg.input(mp3_file_name)
                stream = ffmpeg.filter(stream, "speechnorm", e=6.25, r=0.00001, l=1)
                stream = ffmpeg.output(stream, opus_file_name, acodec="libopus")
                stream = ffmpeg.overwrite_output(stream)
                await self.loop.run_in_executor(None, ffmpeg.run, stream, "ffmpeg", True, True)
            except Exception as e:
                print(e)
                # print stacktrace to console
                traceback.print_exc()
                os.close(opus_file_descriptor)
                with suppress(OSError):
                    os.remove(opus_file_name)
                try:
                    await message.channel.send(f"> ,,{text}\n{e}", reference=message)
                except:
                    pass
                await self.vom_lock.acquire()
                continue
            with suppress(OSError):
                os.remove(mp3_file_name)
            speak_lock = self.speak_lock.get(message.channel.id)
            if not speak_lock:
                speak_lock = asyncio.Lock()
                self.speak_lock[message.channel.id] = speak_lock
            await speak_lock.acquire()
            speak_queue = self.speak_queue.get(message.channel.id)
            if not speak_queue:
                speak_queue = []
                self.speak_queue[message.channel.id] = speak_queue
            self.voming_item = None
            speak_queue.append((message, text, (opus_file_descriptor, opus_file_name)))
            if not self.is_speak_job_running.get(message.channel.id, False):
                self.is_speak_job_running[message.channel.id] = True
                speak_lock.release()
                self.loop.create_task(self.speak_job(message.channel))
            else:
                speak_lock.release()
            await self.vom_lock.acquire()
        self.voming_item = None
        self.vom_lock.release()
        self.is_vom_job_running = False

    async def speak_job(
        self,
        channel: discord.channel.VocalGuildChannel
    ) -> None:
        speak_lock = self.speak_lock.get(channel.id)
        if not speak_lock:
            speak_lock = asyncio.Lock()
            self.speak_lock[channel.id] = speak_lock
        await speak_lock.acquire()
        speak_queue = self.speak_queue.get(channel.id)
        if not speak_queue:
            speak_queue = []
            self.speak_queue[channel.id] = speak_queue
        speaking_queue = self.speaking_queue.get(channel.id)
        if not speaking_queue:
            speaking_queue = []
            self.speaking_queue[channel.id] = speaking_queue
        while speak_queue:
            message, text, (opus_file_descriptor, opus_file_name) = item = speak_queue.pop(0)
            try:
                audio = discord.FFmpegOpusAudio(opus_file_name)
            except Exception as e:
                print(e)
                # print stacktrace to console
                traceback.print_exc()
                os.close(opus_file_descriptor)
                with suppress(OSError):
                    os.remove(opus_file_name)
                try:
                    await message.channel.send(f"> ,,{text}\n{e}", reference=message)
                except:
                    pass
                continue
            speaking_queue.append((*item, audio))
            speak_lock.release()
            print(f"Speak: {opus_file_name}")
            speak_end_event = self.speak_end_events_map.get(channel)
            if not speak_end_event:
                speak_end_event = asyncio.Event()
                speak_end_event.set()
                self.speak_end_events_map[message.channel] = speak_end_event

            def cleanup(
                opus_file_descriptor: int,
                opus_file_name: str,
                /,
                audio: discord.FFmpegOpusAudio
            ) -> None:
                audio.cleanup()
                os.close(opus_file_descriptor)
                with suppress(OSError):
                    os.remove(opus_file_name)

            def complete(
                e: Optional[Exception]
            ) -> None:
                speak_end_event.set()
                message, text, (opus_file_descriptor, opus_file_name), audio = speaking_queue.pop(0)
                cleanup(opus_file_descriptor, opus_file_name, audio)
                print(f"Speak complete: {opus_file_name}")
                if e:
                    print(f"{type(e)}: {e}")
                    traceback.print_exc()
                    self.loop.call_soon(
                        message.channel.send(f"> ,,{text}\n{e}", reference=message, silent=True)
                    )

            async def log_error(
                text: str,
                e: Exception
            ) -> None:
                print(f"{type(e)}: {e}")
                traceback.print_exc()
                with suppress(Exception):
                    await message.channel.send(f"> ,,{text}\n{e}", reference=message, silent=True)

            voice_client = self.connected_voice_client(channel, discord.VoiceClient)
            if voice_client is not None:
                print(f"Found voice client for channel: {message.channel}")
                await speak_end_event.wait()
                speak_end_event.clear()
                try:
                    voice_client.play(audio, after=complete)
                except Exception as e:
                    speak_end_event.set()
                    speaking_queue.pop(0)
                    cleanup(opus_file_descriptor, opus_file_name, audio)
                    await log_error(text, e)
            else:
                print(f"Creating voice client for channel: {message.channel}")
                cont = False
                while True:
                    try:
                        voice_client = await asyncio.wait_for(message.channel.connect(), timeout=10)
                        break
                    except discord.ClientException as e:
                        if len(e.args) > 0:
                            if e.args[0] == "Already connected to a voice channel.":
                                voice_client = self.voice_client(message.channel, discord.VoiceClient)
                                if voice_client is not None:
                                    voice_client.disconnect(force=True)
                                    continue
                                else:
                                    speaking_queue.pop(0)
                                    cleanup(opus_file_descriptor, opus_file_name, audio)
                                    await log_error(text, e)
                                    cont = True
                                    break
                    except Exception as e:
                        speaking_queue.pop(0)
                        cleanup(opus_file_descriptor, opus_file_name, audio)
                        await log_error(text, e)
                        cont = True
                        break
                if cont:
                    await speak_lock.acquire()
                    continue
                await speak_end_event.wait()
                speak_end_event.clear()
                try:
                    voice_client.play(audio, after=complete)
                except Exception as e:
                    speaking_queue.pop(0)
                    cleanup(opus_file_descriptor, opus_file_name, audio)
                    await log_error(text, e)
                    speak_end_event.set()
            await speak_lock.acquire()
        self.voming_item = None
        speak_lock.release()
        self.is_speak_job_running[channel.id] = False

    async def load_enabled(
        self,
        /,
        *,
        path: StrOrBytesPath = "enabled.yaml",
        **kwargs
    ) -> None:
        async with self.enabled_user_ids_lock:
            if os.path.exists(path):
                with open(path, "r") as f:
                    self.enabled_user_ids_map = yaml.safe_load(f) or {}
            else:
                self.enabled_user_ids_map = {}

    async def get_enabled(
        self,
        /,
        *,
        channel: discord.channel.VocalGuildChannel,
        user: Union[discord.User, discord.Member],
        **kwargs
    ) -> bool:
        async with self.enabled_user_ids_lock:
            if self.enabled_user_ids_map:
                if channel in self.enabled_user_ids_map.keys():
                    if user.id in self.enabled_user_ids_map[channel.id]:
                        return True
            return False

    async def update_enabled(
        self,
        enabled: bool,
        /,
        *,
        channel: discord.channel.VocalGuildChannel,
        user: Union[discord.User, discord.Member],
        path: StrOrBytesPath = "enabled.yaml",
        **kwargs
    ) -> None:
        await self.load_enabled(path=path)
        async with self.enabled_user_ids_lock:
            if enabled:
                if channel.id not in self.enabled_user_ids_map.keys():
                    self.enabled_user_ids_map[channel.id] = []
                if user.id not in self.enabled_user_ids_map[channel.id]:
                    self.enabled_user_ids_map[channel.id].append(user.id)
            else:
                if channel.id in self.enabled_user_ids_map.keys():
                    if user.id in self.enabled_user_ids_map[channel.id]:
                        self.enabled_user_ids_map[channel.id].remove(user.id)
                        if not self.enabled_user_ids_map[channel.id]:
                            del self.enabled_user_ids_map[channel.id]
            with open(path, "w") as f:
                yaml.safe_dump(self.enabled_user_ids_map, f)

    async def load_config(
        self,
        /,
        *,
        path: StrOrBytesPath = "config.yaml",
        **kwargs
    ) -> None:
        async with self.user_config_lock:
            if os.path.exists(path):
                with open(path, "r") as f:
                    self.user_config_map = yaml.safe_load(f) or {}
            else:
                self.user_config_map = {}

    @overload
    async def get_config(
        self,
        key: str,
        /,
        *,
        user: Union[discord.User, discord.Member],
        **kwargs
    ) -> Optional[Any]:
        ...

    @overload
    async def get_config(
        self,
        *keys: str,
        user: Union[discord.User, discord.Member],
        **kwargs
    ) -> Optional[Any]:
        ...

    async def get_config(
        self,
        *keys: str,
        user: Union[discord.User, discord.Member],
        **kwargs
    ) -> Optional[Any]:
        async with self.user_config_lock:
            if self.user_config_map:
                if user.id in self.user_config_map.keys():
                    def get_nested(
                        root: dict,
                        keys: list[str]
                    ) -> dict:
                        if not keys:
                            return root
                        if keys[0] in root.keys():
                            return get_nested(root[keys[0]], keys[1:])
                        return {}
                    d = get_nested(self.user_config_map[user.id], list(keys[:-1]))
                    if keys[-1] in d.keys():
                        return d[keys[-1]]
            return None

    @overload
    async def update_config(
        self,
        key: str,
        value: Optional[Any] = None,
        /,
        *,
        user: Union[discord.User, discord.Member],
        path: StrOrBytesPath,
        **kwargs
    ) -> None:
        ...

    @overload
    async def update_config(
        self,
        *keys: str,
        value: Optional[Any],
        user: Union[discord.User, discord.Member],
        path: StrOrBytesPath,
        **kwargs
    ) -> None:
        ...

    async def update_config(
        self,
        *keys_and_value: Union[str, Optional[Any]],
        user: Union[discord.User, discord.Member],
        path: StrOrBytesPath = "config.yaml",
        **kwargs
    ) -> None:
        await self.load_config(path=path)
        async with self.user_config_lock:
            if user.id not in self.user_config_map.keys():
                self.user_config_map[user.id] = {}
            keys: list[str] = []
            value: Optional[Any] = None
            if "value" in kwargs.keys():
                keys = keys_and_value
                value = kwargs["value"]
            elif len(keys_and_value) == 1:
                keys = keys_and_value[0:1]
            else:
                keys = keys_and_value[:-1]
                value = keys_and_value[-1]
            def build_nested(
                root: dict,
                keys: list[str]
            ):
                if not keys:
                    return
                if keys[0] not in root.keys() or not isinstance(root[keys[0]], dict):
                    root[keys[0]] = {}
                build_nested(root[keys[0]], keys[1:])
            build_nested(self.user_config_map[user.id], keys[:-1])
            def get_nested(
                root: dict,
                keys: list[str]
            ) -> dict:
                if not keys:
                    return root
                return get_nested(root[keys[0]], keys[1:])
            d = get_nested(self.user_config_map[user.id], keys[:-1])
            if value is None:
                with suppress(KeyError):
                    del d[keys[-1]]
            else:
                d[keys[-1]] = value
            with open(path, "w") as f:
                yaml.safe_dump(self.user_config_map, f)

    @property
    def connected_voice_clients(
        self
    ) -> list[discord.VoiceProtocol]:
        return [vc for vc in self.voice_clients if vc.is_connected()]

    VoiceClient = TypeVar("VoiceClient", bound=discord.VoiceProtocol)

    @overload
    def voice_client(
        self,
        channel: discord.VoiceChannel,
        /,
    ) -> Optional[discord.VoiceProtocol]:
        ...

    @overload
    def voice_client(
        self,
        channel: discord.VoiceChannel,
        vc_type: Type[VoiceClient],
        /,
    ) -> Optional[VoiceClient]:
        ...

    def voice_client(
        self,
        channel: discord.VoiceChannel,
        vc_type: Optional[Type[VoiceClient]] = None,
        /
    ) -> Optional[VoiceClient]:
        for vc in self.voice_clients:
            if vc_type is None:
                return vc
            elif isinstance(vc, vc_type) and vc.channel == channel:
                return vc
        return None

    @overload
    def connected_voice_client(
        self,
        channel: discord.VoiceChannel,
        /,
    ) -> Optional[discord.VoiceProtocol]:
        ...

    @overload
    def connected_voice_client(
        self,
        channel: discord.VoiceChannel,
        vc_type: Type[VoiceClient],
        /,
    ) -> Optional[VoiceClient]:
        ...

    def connected_voice_client(
        self,
        channel: discord.VoiceChannel,
        vc_type: Optional[Type[VoiceClient]] = None,
        /
    ) -> Optional[VoiceClient]:
        for vc in self.connected_voice_clients:
            if vc_type is None:
                return vc
            elif isinstance(vc, vc_type) and vc.channel == channel:
                return vc
        return None

    async def on_ready(
        self
    ) -> None:
        self.vom = VOM()
        self.enabled_user_ids_lock = asyncio.Lock()
        self.user_config_lock = asyncio.Lock()
        self.vom_lock = asyncio.Lock()
        self.speak_end_events_lock = asyncio.Lock()
        await self.load_enabled()
        await self.load_config()
        await self.refresh_vom_token()

    async def on_message(
        self,
        message: discord.Message
    ) -> None:
        if not isinstance(message.channel, discord.channel.VocalGuildChannel):
            return
        if message.author not in message.channel.members:
            return
        command = self.command_or_none(message)
        if command is not None:
            if message.author.id not in self.user_config_map:
                self.user_config_map[message.author.id] = {}
            command = command.split()
            if len(command) == 0:
                command = [""]
            command[0] = command[0].lower()
            if len(command) == 1:
                if command[0] in ["on", "enable", "1"]:
                    await self.update_enabled(True, channel=message.channel, user=message.author)
                    with suppress(Exception):
                        await message.channel.send("> enable", reference=message, mention_author=False)
                    return
                elif command[0] in ["off", "disable", "0"]:
                    await self.update_enabled(False, channel=message.channel, user=message.author)
                    with suppress(Exception):
                        await message.channel.send("> disable", reference=message, mention_author=False)
                    return
                elif command[0] in ["toggle", "~"]:
                    value = not self.user_config_map[message.author.id]["enabled"]
                    await self.update_enabled(value, channel=message.channel, user=message.author)
                    with suppress(Exception):
                        await message.channel.send(f"> toggle\n{value}", reference=message, mention_author=False)
                    return
                elif command[0] in ["stop", "."]:
                    voice_client = self.connected_voice_client(message.channel, discord.VoiceClient)
                    if voice_client and voice_client.is_playing():
                        voice_client.stop()
                        with suppress(Exception):
                            await message.channel.send("> stop", reference=message, mention_author=False)
                    return
                elif command[0] in ["connect"]:
                    if self.connected_voice_client(message.channel) is None:
                        try:
                            await message.author.voice.channel.connect()
                        except discord.errors.DiscordException as e:
                            with suppress(Exception):
                                await message.channel.send(f"> connect\n{e}", reference=message, mention_author=False)
                        else:
                            with suppress(Exception):
                                await message.channel.send("> connect", reference=message, mention_author=False)
                    return
                elif command[0] in ["quit", "q!"]:
                    voice_client = self.connected_voice_client(message.channel, discord.VoiceClient)
                    if voice_client:
                        if voice_client.is_playing():
                            voice_client.stop()
                        await voice_client.disconnect(force=True)
                        with suppress(Exception):
                            await message.channel.send("> quit", reference=message, mention_author=False)
                    return
                elif command[0] in ["ping", "p"]:
                    now = datetime.now(timezone.utc)
                    lag_delta = now - message.created_at
                    lag_ms = lag_delta.days * 86400000 + lag_delta.seconds * 1000 + lag_delta.microseconds / 1000
                    lag_unit = "msec" + ("s" if lag_ms != 1 else "")
                    with suppress(Exception):
                        await message.channel.send(f"> ping\n{lag_ms:,} {lag_unit}", reference=message, mention_author=False)
                    return
                elif command[0] in ["queue", "q?"]:
                    voice_client = self.connected_voice_client(message.channel, discord.VoiceClient)
                    if not voice_client:
                        return
                    speak_lock = self.speak_lock.get(message.channel.id)
                    if speak_lock:
                        await speak_lock.acquire()
                    async with self.vom_lock:
                        vom_queue = [(*i, None) for i in filter(lambda x: x[0].channel == message.channel, self.vom_queue)]
                        voming_item = self.voming_item
                        if voming_item and voming_item[0].channel == message.channel:
                            vom_queue.insert(0, (*voming_item, None))
                    speak_queue = self.speak_queue.get(message.channel.id, []).copy()
                    speaking_queue = self.speaking_queue.get(message.channel.id, []).copy()
                    if speak_lock:
                        speak_lock.release()
                    unified_queue = sorted(vom_queue + speak_queue + speaking_queue, key=lambda x: x[0].id)
                    str_buffer = StringIO()
                    for message, text, opus_file_name in unified_queue:
                        queue_type = "V" if opus_file_name is None else "S"
                        multiline_text = text.splitlines()
                        first_line = multiline_text[0] + (" …" if len(multiline_text) > 1 else "")
                        str_buffer.write(f"[`{queue_type}`] <{message.author.display_name}> {first_line}\n")
                    str_buffer.seek(0)
                    with suppress(Exception):
                        await message.channel.send(f"> queue\n{str_buffer.read()}", reference=message, mention_author=False)
                    str_buffer.close()
                    return
                elif command[0] in ["refresh"]:
                    command[1] = command[1].lower()
                    if command[1] in ["token", "t"]:
                        try:
                            await self.refresh_vom_token(retry=0)
                        except aiohttp.ClientResponseError as e:
                            with suppress(Exception):
                                await message.channel.send(f"> refresh token\n{e.status}", reference=message, mention_author=False)
                        except Exception as e:
                            with suppress(Exception):
                                await message.channel.send(f"> refresh token\n{e}", reference=message, mention_author=False)
                        else:
                            with suppress(Exception):
                                await message.channel.send("> refresh token", reference=message, mention_author=False)
                    return
                elif command[0] in ["left"]:
                    try:
                        usage = await self.vom.character_usage()
                    except Exception as e:
                        with suppress(Exception):
                            await message.channel.send(f"> left\n{e}", reference=message, mention_author=False)
                    else:
                        with suppress(Exception):
                            await message.channel.send(f"> left\n{usage.characters_available}", reference=message, mention_author=False)
                    return
                elif command[0] in ["help", "?", ""]:
                    if message.author in message.channel.members:
                        try:
                            text = (
                                """
                                `,,`로 시작하는 모든 메시지를 말합니다.

                                `enable`|`on`|`1`
                                    `,,` 없이 말할 때 음성으로 말합니다. `\\,,`로 시작하는 메시지는 음성으로 말하지 않습니다.

                                `disable`|`off`|`0`
                                    `,,` 없이 말할 때 음성으로 말하지 않습니다.

                                `toggle`|`~`
                                    `,,` 없이 말할 때 음성으로 말할지 말지를 전환합니다.

                                `stop`|`.`
                                    음성으로 말하는 것을 중단합니다.

                                `connect`
                                    음성 채널에 들어갑니다.

                                `quit`|`q!`
                                    음성 채널에서 나갑니다.

                                `p`[`ing`]
                                    정상 작동 여부를 확인합니다.

                                `queue`|`q?`
                                    음성으로 말할 메시지 목록을 확인합니다. `V`는 음성 생성을 대기하는 메시지, `S`는 말하기를 대기하는 메시지를 나타냅니다.

                                `refresh`  `t`[`oken`]
                                    음성을 생성할 때 사용하는 토큰을 갱신합니다.

                                `left`
                                    음성을 생성할 수 있는 남은 글자 수를 확인합니다.

                                `g`[`ender`]  [`f`[`emale`]|`m`[`ale`]|`?`]
                                    성별을 설정합니다. `?`로 현재 성별을 확인합니다. 생략하면 성별을 초기화합니다.

                                `v`[`oice`]  <*LOCALE*>  [*VOICE_NAME*|*VOICE_INDEX*|`?`]
                                    음성을 설정합니다. *LOCALE*은 ISO 639-1 언어 코드이거나, ISO 3166-1 국가 코드를 `-`로 연결한 형식입니다. *VOICE_NAME*은 음성 이름입니다. *VOICE_INDEX*는 음성 목록에서의 인덱스입니다. `?`로 현재 음성을 확인합니다. 생략하면 음성을 초기화합니다.

                                `voices`|`v?`  <*LOCALE*>  [*PAGE_NUMBER*]
                                    음성 목록을 표시합니다. *LOCALE*은 ISO 639-1 언어 코드이거나, ISO 3166-1 국가 코드를 `-`로 연결한 형식입니다. 생략하면 1페이지를 표시합니다.

                                `a`[`lias`]|`a!`  [`force`]  <*LANGUAGE*|`~`>  <*REGEX*>  [*ALIAS*]
                                    사용자 정의 에일리어스를 설정합니다. *LANGUAGE*는 *ALIAS*의 언어로, ISO 639-1 언어 코드입니다. `~`로 공용으로 표시합니다. *REGEX*는 *ALIAS*로 지정된 발음으로 대체되는 정규 표현식입니다. 공백 문자는 사용할 수 없지만, 필요한 경우 HTML 엔티티를 사용할 수 있습니다. *ALIAS*는 *REGEX*에 대한 발음입니다. 생략하면 현재 설정된 에일리어스를 표시합니다. 명령에 `a!`를 사용하거나, 첫번째 인수로 `force`를 사용한 경우, 빈 문자열을 *ALIAS*로써 설정합니다.

                                `unalias`|`~a`  <*LANGUAGE*|`~`>  <*REGEX*>
                                    사용자 정의 에일리어스를 삭제합니다. *LANGUAGE*는 *REGEX*에 대한 발음의 언어로, ISO 639-1 언어 코드입니다. `~`로 공용으로 표시합니다. *REGEX*는 사전에 지정된 발음으로 대체되는 정규 표현식입니다. 공백 문자는 사용할 수 없지만, 필요한 경우 HTML 엔티티를 사용할 수 있습니다.

                                [`help`|`?`]
                                    이 도움말을 표시합니다.
                                """
                            )
                            text = dedent(text).strip("\n")
                            await message.channel.send(f"> help\n{text}", reference=message, mention_author=False)
                        except:
                            pass
            if command[0] in ["gender", "g"]:
                if len(command) == 1:
                    await self.update_config("gender", user=message.author)
                    with suppress(Exception):
                        await message.channel.send("> gender", reference=message, mention_author=False)
                elif len(command) == 2:
                    command[1] = command[1].lower()
                    if command[1] in ["male", "m"]:
                        await self.update_config("gender", "male", user=message.author)
                        with suppress(Exception):
                            await message.channel.send("> gender male", reference=message, mention_author=False)
                    elif command[1] in ["female", "f"]:
                        await self.update_config("gender", "female", user=message.author)
                        with suppress(Exception):
                            await message.channel.send("> gender female", reference=message, mention_author=False)
                    elif command[1] == "?":
                        gender = await self.get_config("gender", user=message.author)
                        if gender:
                            with suppress(Exception):
                                await message.channel.send(f"> gender ?\n`{gender}`", reference=message, mention_author=False)
            elif command[0] in ["voice", "v"]:
                if len(command) > 1:
                    # command[1] must be a language code
                    if not self.vom.voices:
                        try:
                            await self.vom.list_voices()
                        except Exception as e:
                            await message.channel.send(f"> voice\n{e}", reference=message, mention_author=False)
                            return
                    language = command[1]
                    voices = self.vom.filter_voices(language)
                    if not voices:
                        if "-" in language:
                            language = language.split("-")[0]
                            voices = self.vom.filter_voices(language)
                        else:
                            starts_with = language + "-"
                            voices = self.vom.filter_voices(starts_with=starts_with)
                    if not voices:
                        return
                    female_voices = []
                    male_voices = []
                    for voice in voices:
                        voice_gender = voice.get("ssmlGender", voice.get("Gender", "")).lower()
                        if voice_gender == "female":
                            female_voices.append(voice)
                        elif voice_gender == "male":
                            male_voices.append(voice)
                    default_voice = self.vom.get_default_voice(user=message.author, voices=voices)
                    default_female_voice = self.vom.get_default_voice(user=message.author, voices=female_voices)
                    default_male_voice = self.vom.get_default_voice(user=message.author, voices=male_voices)
                    voice_name = None
                    female_voice_name = None
                    male_voice_name = None
                    if default_voice:
                        voice_name = default_voice.get("languageName")
                    if default_female_voice:
                        female_voice_name = default_female_voice.get("languageName")
                    if default_male_voice:
                        male_voice_name = default_male_voice.get("languageName")
                    voice_names = ""
                    if voice_name:
                        voice_names += f"`{voice_name}`\n"
                    if female_voice_name:
                        voice_names += f"female: `{female_voice_name}`\n"
                    if male_voice_name:
                        voice_names += f"male: `{male_voice_name}`\n"
                    if len(command) == 2:
                        if voice_names:
                            await self.update_config("voice", language, None, user=message.author)
                            with suppress(Exception):
                                await message.channel.send(f"> voice {language}\n{voice_names[:-1]}", reference=message, mention_author=False)
                    if len(command) > 2:
                        # command[2:] must be a voice name or "?" to get current voice name
                        voice_name = " ".join(command[2:])
                        voice = None
                        if voice_name == "?":
                            voice = await self.get_config("voice", language, user=message.author) or default_voice
                            if voice:
                                name = voice.get("languageName")
                                if name:
                                    with suppress(Exception):
                                        await message.channel.send(f"> voice {language} ?\n`{name}`", reference=message, mention_author=False)
                            return
                        elif voice_name.isdigit():
                            voice_index = int(voice_name) - 1
                            if voice_index in range(len(voices)):
                                voice = voices[voice_index]
                                voice_name = voice.get("languageName")
                                if not voice_name:
                                    return
                        if not voice:
                            for voice in voices:
                                if voice.get("languageName") == voice_name:
                                    break
                            else:
                                return
                        await self.update_config("voice", language, voice_name, user=message.author)
                        with suppress(Exception):
                            await message.channel.send(f"> voice {language} {voice_name}", reference=message, mention_author=False)
            elif command[0] in ["voices", "v?"]:
                if not self.vom.voices:
                    try:
                        await self.vom.list_voices()
                    except Exception as e:
                        await message.channel.send(f"> voices\n{e}", reference=message, mention_author=False)
                        return
                if len(command) > 1:
                    # command[1] must be a language code
                    if len(command) > 3:
                        return
                    language = command[1]
                    voices = self.vom.filter_voices(language)
                    if not voices:
                        if "-" in language:
                            language = language.split("-")[0]
                            voices = self.vom.filter_voices(language)
                        else:
                            starts_with = language + "-"
                            voices = self.vom.filter_voices(starts_with=starts_with)
                    if not voices:
                        return
                    pages = len(voices) // 10 + 1
                    page = command[2] if len(command) > 2 else "1"
                    if page.isdigit():
                        page = int(page)
                    else:
                        return
                    lower = (page - 1) * 10
                    upper = page * 10
                    voices = voices[lower:upper]
                    voice_names = ""
                    for i, voice in enumerate(voices):
                        name = voice.get("languageName")
                        if name:
                            index = lower + i + 1
                            voice_names += f"{index}: `{name}`\n"
                    if voice_names:
                        with suppress(Exception):
                            await message.channel.send(f"> voices {language} {page}\n{voice_names[:-1]}\n… {page} / {pages}", reference=message, mention_author=False)
            elif command[0] in ["alias", "a", "a!"]:
                if len(command) > 1:
                    if command[0] != "a!" and command[1] == "force":
                        command[0] = "a!"
                        command.pop(1)
                if len(command) > 1:
                    destination_language = command[1]
                    if destination_language == "~":
                        destination_language = None
                    word = command[2]
                    if len(command) == 3:  # get or set alias
                        if command[0] == "a!":  # set empty alias
                            alias = ""
                            old_alias = await self.vom.calias(message.channel, None, destination_language, word)
                            await self.vom.set_alias(message.channel, None, destination_language, word, alias)
                            with suppress(Exception):
                                if old_alias:
                                    await message.channel.send(f"> alias force {command[1]} {word}\n{alias}", reference=message, mention_author=False)
                                else:
                                    await message.channel.send(f"> alias force {command[1]} {word}", reference=message, mention_author=False)
                        else:  # get alias
                            alias = await self.vom.calias(message.channel, None, destination_language, word)
                            with suppress(Exception):
                                if alias:
                                    await message.channel.send(f"> alias {command[1]} {word}\n{alias}", reference=message, mention_author=False)
                                else:
                                    await message.channel.send(f"> alias {command[1]} {word}", reference=message, mention_author=False)
                        return
                    if len(command) > 3:  # set alias
                        alias = " ".join(command[3:])
                        old_alias = await self.vom.calias(message.channel, None, destination_language, word)
                        await self.vom.set_alias(message.channel, None, destination_language, word, alias)
                        with suppress(Exception):
                            if old_alias:
                                await message.channel.send(f"> alias {command[1]} {word} {alias}\n{old_alias}", reference=message, mention_author=False)
                            else:
                                await message.channel.send(f"> alias {command[1]} {word} {alias}", reference=message, mention_author=False)
                        return
            elif command[0] in ["unalias", "~a"]:
                if len(command) > 1:
                    destination_language = command[1]
                    if destination_language == "~":
                        destination_language = None
                    word = command[2]
                    old_alias = await self.vom.calias(message.channel, None, destination_language, word)
                    if old_alias is None:
                        return
                    await self.vom.set_alias(message.channel, None, destination_language, word, None)
                    with suppress(Exception):
                        await message.channel.send(f"> unalias {command[1]} {word}\n{old_alias}", reference=message, mention_author=False)
                    return
        else:
            text = self.speak_or_none(message)
            if text:
                await self.vom_lock.acquire()
                self.vom_queue.append((message, text))
                if not self.is_vom_job_running:
                    self.is_vom_job_running = True
                    self.vom_lock.release()
                    self.loop.create_task(self.vom_job())
                else:
                    self.vom_lock.release()

    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ) -> None:
        for voice_client in self.connected_voice_clients:
            if isinstance(voice_client, discord.VoiceClient):
                if voice_client.channel == before.channel:
                    for member in voice_client.channel.members:
                        if not member.bot:
                            break
                    else:
                        if voice_client.is_playing():
                            voice_client.stop()
                        await voice_client.disconnect()
                    break

    @discord.ext.tasks.loop(hours=3)
    async def refresh_vom_token(
        self,
        /,
        retry: int = -1
    ) -> None:
        while True:
            try:
                await self.vom.login(email=self.auth.vom.email, password=self.auth.vom.password)
            except Exception as e:
                print(e)
                if retry == 0:
                    raise e
                retry -= 1
                await asyncio.sleep(0.5)
            else:
                break

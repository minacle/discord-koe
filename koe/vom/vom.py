from __future__ import annotations

from .character_usage import CharacterUsage
from .voice import Voice
import aiohttp
from asyncache import cachedmethod
import asyncio
from cachetools import LFUCache, LRUCache
from cachetools.keys import methodkey
from contextlib import suppress
from copy import deepcopy
import discord
import discord_markdown_ast_parser as markdown
import json
import os
from random import Random
import re
from shelved_cache import PersistentCache
import xml.sax.saxutils
import yaml

from typing import Any, Final, Optional


class VOM:

    Aliases: Final = dict[Optional[str], dict[Optional[str], dict[int, dict[str, str]]]]

    _voices_filename: Final[str] = "data/voices.json"
    _vccache_filename: Final[str] = "data/vccache.shelf"
    _galiases_filename: Final[str] = "data/galiases.yaml"
    _caliases_filename: Final[str] = "data/aliases.yaml"

    def __init__(
        self
    ) -> None:
        self.token: str = ""
        self.voices: list[Voice] = []
        self._galiases: VOM.Aliases = {}
        self._caliases: dict[int, VOM.Aliases] = {}
        self._aliases_cache: LRUCache = LRUCache(maxsize=8, getsizeof=lambda _: 1)
        self._token_lock: asyncio.Lock = asyncio.Lock()
        self._voices_lock: asyncio.Lock = asyncio.Lock()
        self._caliases_lock: asyncio.Lock = asyncio.Lock()
        self._vccache = (
            PersistentCache(
                LFUCache,
                VOM._vccache_filename,
                maxsize=805_306_308,
                getsizeof=lambda x: len(x) if x is not None else 0,
            )
        )
        self.reload_galiases()
        asyncio.create_task(self.reload_caliases())

    async def aliases(
        self,
        channel: discord.abc.VocalGuildChannel
    ) -> VOM.Aliases:

        def deepmerge(
            a: dict[Any, Any],
            b: dict[Any, Any],
            /
        ) -> None:
            for k, v in b.items():
                if k in a:
                    if isinstance(v, dict):
                        deepmerge(a[k], v)
                    else:
                        a[k] = v
                else:
                    a[k] = v

        aliases = self._aliases_cache.get(channel.id)
        if aliases is None:
            aliases = deepcopy(self._galiases)
            async with self._caliases_lock:
                deepmerge(aliases, self._caliases.get(channel.id, {}))
            self._aliases_cache[channel.id] = aliases
        return aliases

    async def set_alias(
        self,
        channel: discord.abc.VocalGuildChannel,
        source_language: Optional[str],
        destination_language: Optional[str],
        word: str,
        alias: Optional[str],
        /
    ) -> None:
        wlen = len(word)
        async with self._caliases_lock:
            if channel.id not in self._caliases:
                self._caliases[channel.id] = {}
            o = self._caliases[channel.id]
            if source_language not in o:
                o[source_language] = {}
            o = o[source_language]
            if destination_language not in o:
                o[destination_language] = {}
            o = o[destination_language]
            if wlen not in o:
                o[wlen] = {}
            o = o[wlen]
            if alias is None:
                if word in o:
                    with suppress(KeyError):
                        del o[word]
            else:
                o[word] = alias
            with open(VOM._caliases_filename, "w") as f:
                yaml.safe_dump(self._caliases, f, allow_unicode=True)
        with suppress(KeyError):
            del self._aliases_cache[channel.id]

    async def calias(
        self,
        channel: discord.abc.VocalGuildChannel,
        source_language: Optional[str],
        destination_language: Optional[str],
        word: str
    ) -> Optional[str]:
        wlen = len(word)
        async with self._caliases_lock:
            if channel.id not in self._caliases:
                self._caliases[channel.id] = {}
            o = self._caliases[channel.id]
            if source_language not in o:
                o[source_language] = {}
            o = o[source_language]
            if destination_language not in o:
                o[destination_language] = {}
            o = o[destination_language]
            if wlen not in o:
                o[wlen] = {}
            o = o[wlen]
            if word in o:
                return o[word]
        return None

    def reload_galiases(
        self
    ) -> None:
        with suppress(FileNotFoundError):
            with open(VOM._galiases_filename, "r") as f:
                self._galiases = yaml.safe_load(f) or {}
        self._aliases_cache.clear()

    async def reload_caliases(
        self
    ) -> None:
        async with self._caliases_lock:
            try:
                with open(VOM._caliases_filename, "r") as f:
                    self._caliases = yaml.safe_load(f) or {}
            except FileNotFoundError:
                open(VOM._caliases_filename, "w").close()
            self._aliases_cache.clear()

    async def login(
        self,
        /,
        *,
        email: str,
        password: str
    ) -> str:
        url = "https://api.voiceovermaker.io/login"
        body = {"email": email, "password": password}
        headers = {"Content-Type": "application/json; charset=utf-8"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body, timeout=3, raise_for_status=True) as response:
                token = json.loads(await response.text())["token"]
        async with self._token_lock:
            self.token = token
        return token

    async def character_usage(
        self,
        /
    ) -> Optional[CharacterUsage]:
        url = "https://api.voiceovermaker.io/character_usage"
        async with self._token_lock:
            headers = {"X-Auth": f"Bearer {self.token}"} if self.token else {}
        headers.update({"Content-Type": "application/json; charset=utf-8"})
        usage = None
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=3, raise_for_status=True) as response:
                usage = json.loads(await response.text())
        if usage is None:
            return None
        return CharacterUsage(
            characters_available=usage["charactersAvailable"],
            total_characters_used=usage["totalCharactersUsed"],
        )

    async def list_voices(
        self,
        /,
        *,
        refresh: bool = False
    ) -> list[Voice]:
        if not refresh:
            if self.voices:
                return self.voices
            if os.path.exists(VOM._voices_filename):
                with open(VOM._voices_filename, "r") as f:
                    voices = json.load(f)
                voice_objects = []
                for voice in voices:
                    voice_objects.append(Voice(voice))
                async with self._voices_lock:
                    self.voices = voice_objects
            else:
                return await self.list_voices(refresh=True)
        else:
            url = "https://api.voiceovermaker.io/list_voices"
            async with self._token_lock:
                headers = {"X-Auth": f"Bearer {self.token}"} if self.token else {}
            headers.update({"Content-Type": "application/json; charset=utf-8"})
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=60, raise_for_status=True) as response:
                    voices = json.loads(await response.text())
            with open(VOM._voices_filename, "w") as f:
                json.dump(voices, f, indent=4)
            voice_objects = []
            for voice in voices:
                voice_objects.append(Voice(voice))
            async with self._voices_lock:
                self.voices = voice_objects
        print(f"Loaded {len(self.voices)} voices.")
        return self.voices

    @cachedmethod(lambda self: self._vccache, key=methodkey)
    async def create_voice(
        self,
        ssml: str,
        speech: Voice,
        /,
        *,
        pitch: float = 0.02,
        speaking_rate: float = 1.38,
    ) -> Optional[bytes]:
        url = "https://api.voiceovermaker.io/create_voice"
        async with self._token_lock:
            headers = {"X-Auth": f"Bearer {self.token}"} if self.token else {}
        headers.update({"Content-Type": "application/json; charset=utf-8"})
        if not ssml:
            return None
        data = {
            "pitch": pitch,
            "returnRawFile": True,
            "speakingRate": speaking_rate,
            "text": ssml,
            "speech": speech._source,
        }
        voice = None
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, timeout=8, raise_for_status=True) as response:
                voice = await response.read()
        return voice

    def filter_voices(
        self,
        language: Optional[str] = None,
        /,
        *,
        starts_with: Optional[str] = None,
        include_deprecated: bool = False,
        include_preview: bool = True,
        only_neural: bool = False,
    ) -> list[Voice]:
        all_voices = self.voices
        voices = []
        for voice in all_voices:
            name = voice.get("name")
            neural = voice.neural
            if isinstance(name, str) and isinstance(neural, bool):
                if "-Neural2-" in name and not neural:
                    continue
            status = voice.get("Status", voice.get("status"))
            if isinstance(status, str):
                if not include_deprecated:
                    status = status.lower()
                    if status == "deprecated":
                        continue
                if not include_preview:
                    status = status.lower()
                    if status == "preview":
                        continue
            if only_neural:
                if isinstance(neural, bool):
                    if not neural:
                        continue
            locale = voice.locale
            if isinstance(locale, str):
                if language:
                    if language == locale:
                        voices.append(voice)
                        continue
                elif starts_with:
                    if locale.startswith(starts_with):
                        voices.append(voice)
                        continue
        return voices

    def get_default_voice(
        self,
        *,
        user: discord.abc.User,
        language: Optional[str] = None,
        voices: Optional[list[Voice]] = None,
        **kwargs
    ) -> Optional[Voice]:
        if not voices:
            voices = self.filter_voices(language)
        if not voices:
            if language and "-" in language:
                language = language.split("-")[0]
                voices = self.filter_voices(language)
            else:
                starts_with = (language or "") + "-"
                voices = self.filter_voices(starts_with=starts_with)
        random = Random(user.id)
        if not voices:
            return None
        voice = random.choice(voices)
        return voice

    async def ssml(
        self,
        text: str,
        /,
        *,
        language: Optional[str],
        channel: discord.abc.VocalGuildChannel
    ) -> str:
        text = re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~])", r"\1", text)
        text = (
            xml.sax.saxutils.escape(
                text,
                entities={
                    '"': "&quot;",
                    "'": "&apos;",
                }
            )
        )
        text = re.sub(r"^&gt;&gt;&gt; ", ">>> ", text)
        text = re.sub(r"^&gt; ", "> ", text)
        root = markdown.parse_to_dict(text)
        def build_text(
            node: dict[str, Any]
        ) -> str:
            if node["node_type"] == "TEXT":
                return node["text_content"]
            elif node["node_type"] in ["ITALIC", "UNDERLINE", "CODE_INLINE"]:
                text = ""
                for child in node.get("children", []):
                    text += build_text(child)
                return f'<emphasis level="moderated">{text}</emphasis>'
            elif node["node_type"] == "BOLD":
                text = ""
                for child in node.get("children", []):
                    text += build_text(child)
                return f'<emphasis level="strong">{text}</emphasis>'
            elif node["node_type"] == "STRIKETHROUGH":
                text = ""
                for child in node.get("children", []):
                    text += build_text(child)
                return f'<emphasis level="reduced">{text}</emphasis>'
            elif node["node_type"] == "QUOTE_BLOCK":
                text = ""
                for child in node.get("children", []):
                    text += build_text(child)
                return f'<prosody pitch="low"><s>{text}</s></prosody>'
            else:
                return ""
        text = ""
        for node in root:
            text += build_text(node)
        if language == "und":
            language = None
        unified_aliases: dict[int, dict[str, str]] = {}
        aliases = await self.aliases(channel)
        for d in aliases.values():
            for (lang_dest, d) in d.items():
                if lang_dest in [None, language]:
                    unified_aliases.update(d)
        untouched_text = text
        aliased_text_parts: list[tuple[int, int, str]] = []  # (start, end, result)
        for (_, d) in sorted(unified_aliases.items(), key=lambda x: x[0], reverse=True):
            for (word, alias) in sorted(d.items(), key=lambda x: len(x[0]), reverse=True):
                while True:
                    m = re.search(word, untouched_text)
                    if not m:
                        break
                    start = m.start()
                    end = m.end()
                    aliased_text_parts.append((start, end, f"<sub alias={xml.sax.saxutils.quoteattr(alias)}>{m.group()}</sub>"))
                    untouched_text = untouched_text[:start] + " " * (end - start) + untouched_text[end:]
        aliased_text_parts.sort(key=lambda x: x[0], reverse=True)
        for start, end, result in aliased_text_parts:
            text = text[:start] + result + text[end:]
        text = re.sub(r'<sub alias="">(.+?)</sub>', "", text)
        while True:
            m = re.search(r'<sub alias="([^ ]*?)">(.+?)</sub><sub alias="([^ ]*?)">(.+?)</sub>', text)
            if not m:
                break
            start = m.start()
            end = m.end()
            text = text[:start] + f'<sub alias="{m.group(1)}{m.group(3)}">{m.group(2)}{m.group(4)}</sub>' + text[end:]
        lines = text.splitlines()
        text = ""
        for line in lines:
            line = line.strip()
            if not line:
                continue
            text += f"<p>{line}</p>"
        return text

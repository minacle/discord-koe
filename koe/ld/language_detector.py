from __future__ import annotations

import aiohttp
from asyncache import cachedmethod
from cachetools import LFUCache
from cachetools.keys import methodkey
import json
from shelved_cache import PersistentCache

from typing import Final


class LanguageDetector:

    _ldcache: Final = (
        PersistentCache(
            LFUCache,
            "ldcache",
            maxsize=1_048_576,
            getsizeof=lambda x: len(x) + 1,
        )
    )

    def __init__(
        self,
        /,
        *,
        api_key: str,
        timeout: float = 4,
    ) -> None:
        self._api_key: str
        self._url: str
        self.timeout: float = timeout
        self.api_key = api_key

    @property
    def api_key(
        self
    ) -> str:
        return self._api_key

    @api_key.setter
    def api_key(
        self,
        api_key: str
    ) -> None:
        self._api_key = api_key
        self._url: str = f"https://translation.googleapis.com/language/translate/v2/detect?key={api_key}"

    @cachedmethod(lambda self: LanguageDetector._ldcache, key=methodkey)
    async def detect(
        self,
        text: str,
    ) -> str:
        headers = {"Content-Type": "application/json; charset=utf-8"}
        body = {"q": text}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self._url, headers=headers, json=body, timeout=self.timeout) as response:
                    language = json.loads(await response.text())["data"]["detections"][0][0]["language"]
        except:
            language = "und"
        return language

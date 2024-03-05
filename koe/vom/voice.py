from __future__ import annotations

import collections.abc

from typing import Any


class Voice(collections.abc.Hashable, collections.abc.Mapping):

    def __init__(
        self,
        d: dict,
        /
    ) -> None:
        self._source: dict = d

    def __hash__(
        self
    ) -> int:
        return hash(
            (
                self.language_name,
                self.pvr,
                self.neural,
                self.internal_id,
                self.locale,
            )
        )

    def __getitem__(
        self,
        key: str
    ) -> Any:
        return self._source[key]

    def __iter__(
        self,
    ) -> collections.abc.Iterator[str]:
        return iter(self._source)

    def __len__(
        self
    ) -> int:
        return len(self._source)

    def __contains__(
        self,
        key: object,
    ) -> bool:
        return key in self._source

    @property
    def language_name(
        self
    ) -> str:
        return self["languageName"]

    @property
    def pvr(
        self
    ) -> str:
        return self["pvr"]

    @property
    def neural(
        self
    ) -> bool:
        return self["neural"]

    @property
    def internal_id(
        self
    ) -> str:
        return self["internalId"]

    @property
    def locale(
        self
    ) -> str:
        return self["locale"]

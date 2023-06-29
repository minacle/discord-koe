from __future__ import annotations

import os

from typing import Optional


class Discord:

    def __init__(
        self,
        /,
        *,
        token: Optional[str] = None,
    ) -> None:
        if token is None:
            token = os.environ.get("DISCORD_TOKEN")
        if token is None:
            raise ValueError("No token provided.")
        self.token: str = token

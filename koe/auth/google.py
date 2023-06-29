from __future__ import annotations

import os

from typing import Optional


class Google:

    def __init__(
        self,
        /,
        *,
        api_key: Optional[str] = None,
    ) -> None:
        if api_key is None:
            api_key = os.environ.get("GOOGLE_API_KEY")
        if api_key is None:
            raise ValueError("No API key provided.")
        self.api_key: str = api_key

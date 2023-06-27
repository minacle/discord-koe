from __future__ import annotations

import os

from typing import Optional


class VOM:

    def __init__(
        self,
        /,
        *,
        email: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        if email is None:
            email = os.environ.get("VOM_EMAIL")
        if password is None:
            password = os.environ.get("VOM_PASSWORD")
        if email is None or password is None:
            raise ValueError("No email or password provided.")
        self.email: str = email
        self.password: str = password

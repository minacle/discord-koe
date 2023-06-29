from .discord import Discord
from .google import Google
from .vom import VOM


class Auth:

    def __init__(
        self,
        /,
        *,
        discord: Discord,
        google: Google,
        vom: VOM,
        **kwargs,
    ) -> None:
        self.discord: Discord = discord
        self.google: Google = google
        self.vom: VOM = vom


__all__ = (
    "Discord",
    "Google",
    "VOM",
)

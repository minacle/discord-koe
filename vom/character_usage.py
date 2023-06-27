from __future__ import annotations


class CharacterUsage:

    def __init__(
        self,
        characters_available: int,
        total_characters_used: int,
    ) -> None:
        self.characters_available: int = characters_available
        self.total_characters_used: int = total_characters_used

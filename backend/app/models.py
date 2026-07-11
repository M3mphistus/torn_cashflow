from dataclasses import dataclass, field


@dataclass
class CurrentPlayer:
    player_id: int
    name: str | None
    faction_id: int | None
    api_key: str = field(repr=False)

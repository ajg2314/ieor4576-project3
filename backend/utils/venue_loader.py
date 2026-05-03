from pathlib import Path
import yaml
from backend.models.schemas import VenueContext

_VENUE_DIR = Path(__file__).parent.parent / "venues"
_VENUE_CACHE: dict[str, VenueContext] = {}


def load_venues() -> None:
    for path in _VENUE_DIR.glob("*.yaml"):
        data = yaml.safe_load(path.read_text())
        _VENUE_CACHE[data["venue"]] = VenueContext(**data)


def get_venue_context(venue: str) -> VenueContext | None:
    return _VENUE_CACHE.get(venue)

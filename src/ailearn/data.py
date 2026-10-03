"""Dataset metadata and an opt-in provider registry without automatic downloads."""

from typing import Protocol

from pydantic import Field, HttpUrl

from ailearn.models import Model


class Dataset(Model):
    id: str
    source: str
    url: HttpUrl
    variables: dict[str, str]
    units: dict[str, str]
    frequency: str
    temporal_coverage: str
    geographic_coverage: str
    caveats: list[str]
    synthetic: bool = False


class Requirements(Model):
    domain: str
    frequency: str
    min_observations: int = Field(ge=1)
    required_characteristics: list[str] = Field(default_factory=list)
    preferred_sources: list[str] = Field(default_factory=list)


class Provider(Protocol):
    def discover(self, requirements: Requirements) -> list[Dataset]: ...


class Registry:
    def __init__(self):
        self.providers: dict[str, Provider] = {}

    def register(self, name: str, provider: Provider):
        if name in self.providers:
            raise ValueError(f"provider already registered: {name}")
        self.providers[name] = provider

    def discover(self, name: str, requirements: Requirements) -> list[Dataset]:
        if name not in self.providers:
            raise ValueError(f"unknown provider: {name}")
        return [Dataset.model_validate(d) for d in self.providers[name].discover(requirements)]


SOURCES = {
    "gus-bdl": "https://bdl.stat.gov.pl/",
    "eurostat": "https://ec.europa.eu/eurostat/",
    "nbp": "https://api.nbp.pl/",
    "ecb": "https://data.ecb.europa.eu/",
    "oecd": "https://data-explorer.oecd.org/",
    "world-bank": "https://data.worldbank.org/",
}

"""Pack loading and deterministic dependency validation."""

from importlib.resources import files
from pathlib import Path

import yaml

from ailearn.models import Competency, Dimension, Domain


def load_domains(custom: Path | None = None) -> list[Domain]:
    resources = files("ailearn").joinpath("resources/domains")
    packs = [
        Domain.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
        for p in sorted(resources.iterdir(), key=lambda p: p.name)
        if p.name.endswith(".yml")
    ]
    if custom:
        if not custom.is_dir():
            raise ValueError(f"custom packs directory does not exist: {custom}")
        if not list(custom.glob("*.yml")):
            raise ValueError(f"no .yml domain packs found in {custom}")
        packs.extend(
            Domain.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
            for p in sorted(custom.glob("*.yml"))
        )
    Graph(packs)
    return packs


def required(depth: str) -> list[Dimension]:
    dimensions = [Dimension.CONCEPTUAL, Dimension.INTERPRETATION]
    if depth != "minimal":
        dimensions += [Dimension.MATHEMATICAL, Dimension.IMPLEMENTATION]
    if depth == "comprehensive":
        dimensions += [Dimension.DEBUGGING]
    return dimensions


class Graph:
    def __init__(self, domains: list[Domain]):
        self.domains = {d.id: d for d in domains}
        if len(self.domains) != len(domains):
            raise ValueError("duplicate domain IDs")
        self.nodes: dict[str, Competency] = {}
        for domain in domains:
            for node in domain.competencies:
                if node.id in self.nodes:
                    raise ValueError(f"duplicate competency: {node.id}")
                self.nodes[node.id] = node
        for node in self.nodes.values():
            for dependency in node.prerequisites:
                if dependency not in self.nodes:
                    raise ValueError(f"missing prerequisite: {dependency}")
            if not set(Dimension) <= set(node.outcomes):
                raise ValueError(f"missing dimension outcomes: {node.id}")
        self.closure(list(self.nodes))
        for domain in domains:
            if set(domain.targets) != {"beginner", "mid", "advanced"}:
                raise ValueError(f"missing targets: {domain.id}")
            for targets in domain.targets.values():
                if not targets:
                    raise ValueError("target cannot be empty")
                self.closure(targets)

    def closure(self, targets: list[str]) -> list[str]:
        result: list[str] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(key: str):
            if key not in self.nodes:
                raise ValueError(f"unknown competency: {key}")
            if key in visiting:
                raise ValueError(f"dependency cycle at {key}")
            if key in visited:
                return
            visiting.add(key)
            for dependency in self.nodes[key].prerequisites:
                visit(dependency)
            visiting.remove(key)
            visited.add(key)
            result.append(key)

        for target in targets:
            visit(target)
        return result

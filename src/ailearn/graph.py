"""Pack loading and deterministic dependency validation."""

from pathlib import Path

import yaml

from ailearn.models import Competency, Dimension, Domain


def load_domains(custom: Path | None = None) -> list[Domain]:
    if custom is None or not custom.is_dir():
        raise ValueError("a course requires an agent-authored domain pack directory")
    files_to_load = sorted(custom.glob("*.yml"))
    if not files_to_load:
        raise ValueError(f"no .yml domain packs found in {custom}")
    packs = [
        Domain.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        for path in files_to_load
    ]
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

    def target_closure(self, domain_id: str, target_id: str) -> list[str]:
        """Resolve an agent-authored target and its complete prerequisite graph."""
        domain = self.domains.get(domain_id)
        if domain is None:
            raise ValueError(f"unknown domain: {domain_id}")
        targets = domain.targets.get(target_id)
        if targets is None:
            raise ValueError(f"unknown target {target_id!r} for domain {domain_id!r}")
        return self.closure(targets)

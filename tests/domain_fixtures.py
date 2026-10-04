"""Explicit example curricula used only to exercise graph behavior in tests."""

from pathlib import Path

from ailearn.graph import load_domains

PACKS = Path(__file__).parent / "fixtures" / "domains"


def load_test_domains():
    return load_domains(PACKS)

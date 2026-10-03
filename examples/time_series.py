"""Executable state-engine walkthrough, with explicitly simulated assessor outputs."""

from pathlib import Path
from tempfile import TemporaryDirectory

from ailearn.engine import next_action, record
from ailearn.graph import load_domains
from ailearn.models import Config, Dimension, Evidence
from ailearn.store import Store


def main():
    with TemporaryDirectory() as directory:
        store = Store(Path(directory))
        store.init(Config(domain="time-series", target="beginner", depth="minimal"), load_domains())
        with store.transaction() as state:
            # These are simulation fixtures, never real learner mastery claims.
            for key in ["statistics.mean", "statistics.variance"]:
                for dimension in [Dimension.CONCEPTUAL, Dimension.INTERPRETATION]:
                    for attempt in ["one", "two"]:
                        record(
                            state,
                            Evidence(
                                id=f"{key}-{dimension}-{attempt}",
                                attempt_id=f"{key}-{attempt}",
                                competency=key,
                                dimension=dimension,
                                score=3,
                                independent=True,
                                confidence=0.9,
                                assessor="SIMULATED",
                                artifact="SIMULATED",
                            ),
                        )
            print("Diagnostic target:", next_action(state)["competency"])
            record(
                state,
                Evidence(
                    id="covariance-gap",
                    attempt_id="covariance-diagnostic",
                    competency="statistics.covariance",
                    dimension="interpretation",
                    score=1,
                    independent=True,
                    confidence=0.9,
                    assessor="SIMULATED",
                    artifact="SIMULATED",
                    kind="diagnostic",
                    misconceptions=["Covariance proves causality"],
                ),
            )
            print("Gap routes to:", next_action(state)["scope"])
            for dimension in [Dimension.CONCEPTUAL, Dimension.INTERPRETATION]:
                for attempt in ["one", "two"]:
                    record(
                        state,
                        Evidence(
                            id=f"covariance-{dimension}-{attempt}",
                            attempt_id=f"covariance-{attempt}",
                            competency="statistics.covariance",
                            dimension=dimension,
                            score=3,
                            independent=True,
                            confidence=0.9,
                            assessor="SIMULATED",
                            artifact="SIMULATED",
                            resolves=["Covariance proves causality"],
                        ),
                    )
            print("Repaired; next prerequisite:", next_action(state)["competency"])
            for dimension in [Dimension.CONCEPTUAL, Dimension.INTERPRETATION]:
                for attempt in ["one", "two"]:
                    record(
                        state,
                        Evidence(
                            id=f"correlation-{dimension}-{attempt}",
                            attempt_id=f"correlation-{attempt}",
                            competency="statistics.correlation",
                            dimension=dimension,
                            score=3,
                            independent=True,
                            confidence=0.9,
                            assessor="SIMULATED",
                            artifact="SIMULATED",
                        ),
                    )
            print("Back to original goal:", next_action(state)["competency"])


if __name__ == "__main__":
    main()

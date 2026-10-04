"""Write short, numbered learner tasks without executing their Python code."""

import ast

from ailearn.graph import Graph
from ailearn.models import Exercise, ExerciseArtifact
from ailearn.store import Store


def create_exercise(store: Store, exercise: Exercise) -> ExerciseArtifact:
    exercise = Exercise.model_validate(exercise.model_dump())
    stem = (
        f"lesson_{exercise.lesson:03d}_topic_{exercise.topic:03d}_"
        f"attempt_{exercise.attempt:03d}_{exercise.competency.replace('.', '_')}"
    )
    identifier = f"L{exercise.lesson:03d}-T{exercise.topic:03d}-A{exercise.attempt:03d}"
    header = [
        f"# Lesson {exercise.lesson:03d} | Topic {exercise.topic:03d} | "
        f"Attempt {exercise.attempt:03d}",
        f"# Competency: {exercise.competency} | Kind: {exercise.kind}",
    ]
    content = "\n".join(header + [f"# {line}" for line in exercise.instructions.splitlines()])
    content += "\n\n" + exercise.source.rstrip() + "\n"
    if len(content.splitlines()) > 80:
        raise ValueError("exercise must fit in 80 lines including instructions")
    ast.parse(content)  # Syntax validation only; never executes learner or generated code.
    destination = store.workspace / "lessons" / f"{stem}.py"
    if (
        destination.parent.is_symlink()
        or destination.parent.is_junction()
        or not destination.resolve().is_relative_to(store.workspace)
    ):
        raise ValueError("exercise directory cannot be redirected")
    artifact = ExerciseArtifact(
        id=identifier,
        lesson=exercise.lesson,
        topic=exercise.topic,
        attempt=exercise.attempt,
        competency=exercise.competency,
        kind=exercise.kind,
        path=destination.relative_to(store.workspace).as_posix(),
    )
    created = False
    try:
        with store.transaction() as state:
            if exercise.competency not in Graph(state.domains).nodes:
                raise ValueError("unknown exercise competency")
            if (
                state.intake is not None
                and state.intake.baseline is None
                and exercise.kind != "diagnostic"
            ):
                raise ValueError("baseline must be diagnosed before practice tasks")
            if any(task.id == identifier for task in state.exercises):
                raise ValueError("lesson/topic/attempt already exists; use a new attempt number")
            if any(
                task.lesson == exercise.lesson
                and task.topic == exercise.topic
                and task.competency != exercise.competency
                for task in state.exercises
            ):
                raise ValueError("lesson/topic number is already assigned to another competency")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("x", encoding="utf-8") as stream:
                stream.write(content)
            created = True
            state.exercises.append(artifact)
            state.history.append({"event": "exercise-created", **artifact.model_dump(mode="json")})
    except Exception:
        # Roll back our new scaffold if snapshot publication fails, preserving any learner edits.
        if created and destination.exists() and destination.read_text("utf-8") == content:
            destination.unlink()
        raise
    return artifact


def validate_artifacts(store: Store) -> None:
    for task in store.load().exercises:
        destination = (store.workspace / task.path).resolve()
        if not destination.is_relative_to(store.workspace) or destination.suffix != ".py":
            raise ValueError(f"invalid exercise path: {task.path}")
        if not destination.is_file():
            raise ValueError(f"exercise file is missing: {task.path}")

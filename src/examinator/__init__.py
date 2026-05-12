"""Examinator: generate higher-education exam tasks from study material."""

from examinator.core.agent import build_agent_for_task
from examinator.core.schemas import (
    EinsendeaufgabeQAPair,
    HausarbeitQAPair,
    JobConfig,
    KlausurQAPair,
    PageQuestions,
    ProjektarbeitQAPair,
    TaskType,
)

__all__ = [
    "EinsendeaufgabeQAPair",
    "HausarbeitQAPair",
    "JobConfig",
    "KlausurQAPair",
    "PageQuestions",
    "ProjektarbeitQAPair",
    "TaskType",
    "build_agent_for_task",
]
__version__ = "0.1.0"

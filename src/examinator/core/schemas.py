"""Pydantic schemas for the four exam-task types and the job configuration.

The four output schemas (`HausarbeitQAPair`, `ProjektarbeitQAPair`,
`KlausurQAPair`, `EinsendeaufgabeQAPair`) mirror the OutputFormat sections of
the four system prompts in [docs/walkthrough.md] style 1:1. `PageQuestions[T]`
is the generic container the LLM is asked to return.

`JobConfig` is the parsed multipart-form payload sent by the frontend; it
uses a discriminated union on ``task_type`` so the API can validate each
variant strictly.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enums & shared primitives
# ---------------------------------------------------------------------------


class TaskType(StrEnum):
    """The four supported assignment types."""

    HAUSARBEIT = "hausarbeit"
    PROJEKTARBEIT = "projektarbeit"
    KLAUSUR = "klausur"
    EINSENDEAUFGABE = "einsendeaufgabe"


class AcademicLevel(StrEnum):
    BACHELOR = "Bachelor"
    MASTER = "Master"


class DifficultyLevel(StrEnum):
    LEICHT = "leicht"
    MITTEL = "mittel"
    SCHWER = "schwer"


class QuestionFocus(StrEnum):
    """Klausur-only: controls which subtypes are emitted."""

    KNOWLEDGE = "knowledge"
    TRANSFER = "transfer"
    MIXED = "mixed"


# ---------------------------------------------------------------------------
# Per-task QA-pair schemas — fields line up with the OutputFormat blocks of
# the four system prompts in the original task description.
# ---------------------------------------------------------------------------


class _BaseQAPair(BaseModel):
    """Common fields shared by all four task types."""

    model_config = ConfigDict(extra="ignore")

    question: str = Field(description="The formulated exam question.")
    academic_level: AcademicLevel
    scope: str = Field(description="Free-text scope description (words/points/time).")
    core_topic: str = Field(description="The specific core topic this question relates to.")
    guideline_examiner: str = Field(
        description="Short paragraph (2-4 sentences) on evaluation focus."
    )
    guideline_student: str = Field(
        description="Structured step-by-step roadmap for students."
    )
    source_page: int = Field(
        ge=1, description="1-based page number of the source material this is grounded in."
    )


class HausarbeitQAPair(_BaseQAPair):
    """Hausarbeit (term paper). Bewertungsschema as rubric, no Musterloesung."""

    question_type: Literal["Analytische Frage", "Anwendungs- und Forschungsfrage"]
    bewertungsschema_rubric: str = Field(
        description=(
            "Assessment rubric with formale (20%) and inhaltliche (80%) criteria, "
            "point distribution as bullet points, default total = 120 pts."
        )
    )


class ProjektarbeitQAPair(_BaseQAPair):
    """Projektarbeit (project work). Plain-text rubric Projektskizze 30% / Endergebnis 70%."""

    question_type: Literal["Projektarbeit"] = "Projektarbeit"
    execution_format: str = Field(
        description="Bericht, Praesentation, Visualisierung, empirisch, Konzeptentwicklung, ..."
    )
    bewertungsschema_rubric: str = Field(
        description=(
            "Plain-text assessment rubric: Projektskizze 30% (formal + inhaltlich) "
            "and Endergebnis 70% (formal 15% + inhaltlich 55%)."
        )
    )


class KlausurQAPair(_BaseQAPair):
    """Klausur (closed-book exam). Includes Musterloesung text + rubric."""

    question_type: Literal["Klausurfrage"] = "Klausurfrage"
    klausur_subtype: Literal["Knowledge", "Transfer", "Advanced/Reflection"]
    difficulty_level: DifficultyLevel
    musterloesung_text: str = Field(
        description="Model answer, ~400 words academic style, no citations."
    )
    musterloesung_rubric: str = Field(
        description="Rubric with Teilpunkte, formale + inhaltliche Kriterien summing to total."
    )


class EinsendeaufgabeQAPair(_BaseQAPair):
    """Einsendeaufgabe (open-book booklet assignment). Includes Musterloesung text + rubric."""

    question_type: Literal["Einsendeaufgabe"] = "Einsendeaufgabe"
    einsende_subtype: Literal["Knowledge", "Transfer", "Reflection"]
    difficulty_level: DifficultyLevel
    musterloesung_text: str = Field(
        description="Model answer ~400 words, grounded in the study booklet, no citations."
    )
    musterloesung_rubric: str = Field(
        description="Rubric with Teilpunkte, formale + inhaltliche Kriterien summing to total."
    )


QAPair = HausarbeitQAPair | ProjektarbeitQAPair | KlausurQAPair | EinsendeaufgabeQAPair

T = TypeVar(
    "T",
    HausarbeitQAPair,
    ProjektarbeitQAPair,
    KlausurQAPair,
    EinsendeaufgabeQAPair,
)


class PageQuestions(BaseModel, Generic[T]):
    """Container the LLM is asked to return per prompt run."""

    questions: list[T] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# JobConfig: validated input from the frontend (multipart form, JSON part).
# ---------------------------------------------------------------------------


class _BaseJobConfig(BaseModel):
    """Common parameters across all task types."""

    model_config = ConfigDict(extra="forbid")

    language: str = Field(default="Deutsch", min_length=2, max_length=64)
    extraction_instructions: str = Field(default="", max_length=4000)
    core_topics: list[str] = Field(default_factory=list, max_length=20)
    academic_level: AcademicLevel = AcademicLevel.BACHELOR
    # Optional override for the default scope text injected into the prompt.
    scope_override: str | None = Field(default=None, max_length=300)
    # Optional override for the total point budget where applicable (Hausarbeit
    # default 120 / Klausur default 20 / Einsende default 20).
    total_points: int | None = Field(default=None, ge=1, le=10_000)


class HausarbeitJobConfig(_BaseJobConfig):
    task_type: Literal[TaskType.HAUSARBEIT] = TaskType.HAUSARBEIT


class ProjektarbeitJobConfig(_BaseJobConfig):
    task_type: Literal[TaskType.PROJEKTARBEIT] = TaskType.PROJEKTARBEIT
    execution_format: str = Field(
        default="Schriftlicher Projektbericht (3.500-4.500 Woerter)",
        min_length=3,
        max_length=300,
    )


class KlausurJobConfig(_BaseJobConfig):
    task_type: Literal[TaskType.KLAUSUR] = TaskType.KLAUSUR
    question_focus: QuestionFocus = QuestionFocus.MIXED


class EinsendeaufgabeJobConfig(_BaseJobConfig):
    task_type: Literal[TaskType.EINSENDEAUFGABE] = TaskType.EINSENDEAUFGABE


JobConfig = Annotated[
    HausarbeitJobConfig
    | ProjektarbeitJobConfig
    | KlausurJobConfig
    | EinsendeaufgabeJobConfig,
    Field(discriminator="task_type"),
]


# ---------------------------------------------------------------------------
# Job-status payloads for the API / SSE stream.
# ---------------------------------------------------------------------------


class ProgressEvent(BaseModel):
    """Server-sent event payload describing job progress."""

    stage: Literal[
        "queued",
        "parsing",
        "chunking",
        "chunk_started",
        "chunk_done",
        "reducing",
        "done",
        "error",
    ]
    message: str = ""
    current: int = 0
    total: int = 0


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


def qa_pair_type_for(task_type: TaskType) -> type[QAPair]:
    """Return the concrete QA-pair class for the given task type."""
    match task_type:
        case TaskType.HAUSARBEIT:
            return HausarbeitQAPair
        case TaskType.PROJEKTARBEIT:
            return ProjektarbeitQAPair
        case TaskType.KLAUSUR:
            return KlausurQAPair
        case TaskType.EINSENDEAUFGABE:
            return EinsendeaufgabeQAPair

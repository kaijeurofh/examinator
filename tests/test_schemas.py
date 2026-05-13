"""Tests for the Pydantic schemas in `examinator.core.schemas`."""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from examinator.core.schemas import (
    AcademicLevel,
    DifficultyLevel,
    EinsendeaufgabeJobConfig,
    EinsendeaufgabeQAPair,
    HausarbeitJobConfig,
    HausarbeitQAPair,
    JobConfig,
    KlausurJobConfig,
    KlausurQAPair,
    PageQuestions,
    ProjektarbeitJobConfig,
    ProjektarbeitQAPair,
    QuestionFocus,
    TaskType,
    qa_pair_type_for,
)


def test_hausarbeit_qa_pair_round_trip() -> None:
    pair = HausarbeitQAPair(
        question="Discuss X.",
        question_type="Analytische Frage",
        academic_level=AcademicLevel.BACHELOR,
        scope="3.500-4.500 Woerter",
        core_topic="Topic A",
        guideline_examiner="Focus on analysis.",
        guideline_student="Step-by-step roadmap.",
        bewertungsschema_rubric="Bullet rubric.",
        source_page=1,
    )
    assert pair.source_page == 1
    dumped = pair.model_dump()
    HausarbeitQAPair.model_validate(dumped)


def test_klausur_qa_pair_requires_subtype_and_difficulty() -> None:
    with pytest.raises(ValidationError):
        KlausurQAPair.model_validate(
            {
                "question": "X",
                "academic_level": "Bachelor",
                "scope": "20 pts",
                "core_topic": "T",
                "guideline_examiner": "e",
                "guideline_student": "s",
                "musterloesung_text": "x",
                "musterloesung_rubric": "y",
                "source_page": 1,
                # missing klausur_subtype + difficulty_level
            }
        )


def test_einsendeaufgabe_subtype_constrained() -> None:
    with pytest.raises(ValidationError):
        EinsendeaufgabeQAPair.model_validate(
            {
                "question": "X",
                "academic_level": "Bachelor",
                "scope": "20 pts",
                "core_topic": "T",
                "guideline_examiner": "e",
                "guideline_student": "s",
                "einsende_subtype": "NotAllowed",
                "difficulty_level": "leicht",
                "musterloesung_text": "x",
                "musterloesung_rubric": "y",
                "source_page": 1,
            }
        )


def test_page_questions_is_generic() -> None:
    container: PageQuestions[KlausurQAPair] = PageQuestions(
        questions=[
            KlausurQAPair(
                question="X",
                klausur_subtype="Knowledge",
                difficulty_level=DifficultyLevel.LEICHT,
                academic_level=AcademicLevel.BACHELOR,
                scope="20 pts",
                core_topic="T",
                guideline_examiner="e",
                guideline_student="s",
                musterloesung_text="x",
                musterloesung_rubric="y",
                source_page=2,
            )
        ]
    )
    assert len(container.questions) == 1
    assert container.questions[0].source_page == 2


def test_job_config_discriminator_picks_klausur() -> None:
    adapter: TypeAdapter[JobConfig] = TypeAdapter(JobConfig)
    config = adapter.validate_python(
        {
            "task_type": "klausur",
            "language": "Deutsch",
            "core_topics": ["A", "B"],
            "academic_level": "Master",
            "question_focus": "transfer",
        }
    )
    assert isinstance(config, KlausurJobConfig)
    assert config.question_focus is QuestionFocus.TRANSFER


def test_job_config_rejects_unknown_task_type() -> None:
    adapter: TypeAdapter[JobConfig] = TypeAdapter(JobConfig)
    with pytest.raises(ValidationError):
        adapter.validate_python({"task_type": "unknown"})


def test_job_config_extra_forbid() -> None:
    """Typos in field names should fail loudly, not get silently dropped."""
    with pytest.raises(ValidationError):
        HausarbeitJobConfig.model_validate({"task_type": "hausarbeit", "unkown_field": True})


def test_projektarbeit_execution_format_default() -> None:
    config = ProjektarbeitJobConfig(task_type=TaskType.PROJEKTARBEIT)
    assert "Projektbericht" in config.execution_format


def test_einsendeaufgabe_defaults_to_bachelor() -> None:
    config = EinsendeaufgabeJobConfig(task_type=TaskType.EINSENDEAUFGABE)
    assert config.academic_level is AcademicLevel.BACHELOR


def test_qa_pair_type_for_returns_correct_class() -> None:
    assert qa_pair_type_for(TaskType.HAUSARBEIT) is HausarbeitQAPair
    assert qa_pair_type_for(TaskType.PROJEKTARBEIT) is ProjektarbeitQAPair
    assert qa_pair_type_for(TaskType.KLAUSUR) is KlausurQAPair
    assert qa_pair_type_for(TaskType.EINSENDEAUFGABE) is EinsendeaufgabeQAPair

"""System prompts for the four task types.

The original prompts (provided in the project brief) contain `<AcademicLevel>`
and `<ExecutionFormat>` blocks that instruct the model to ask the user
interactively. Since the web app collects those values up-front via the
frontend form, those blocks are removed here and the values are injected as
constants.

For the chunked-with-overlap generation strategy we expose two prompt
families per task type:

* ``*_CANDIDATE_PROMPT`` — runs once per chunk, asks for *up to* N candidate
  questions grounded in that chunk's pages.
* ``*_REDUCER_PROMPT`` — runs once at the end with all candidates as input,
  asked to produce **exactly 10** final, deduplicated, non-overlapping
  questions across the whole document.
"""

from __future__ import annotations

from examinator.core.schemas import (
    AcademicLevel,
    EinsendeaufgabeJobConfig,
    HausarbeitJobConfig,
    JobConfig,
    KlausurJobConfig,
    ProjektarbeitJobConfig,
    QuestionFocus,
    TaskType,
)

# Number of candidate questions we ask the LLM to produce per chunk.
# 4 candidates * ~6 chunks = ~24 candidates -> reducer picks the best 10.
CANDIDATES_PER_CHUNK = 4

# ---------------------------------------------------------------------------
# Hausarbeit
# ---------------------------------------------------------------------------

_HAUSARBEIT_BASE = """\
You are an expert assistant specialized in creating academic term paper
questions (Hausarbeiten) for higher education, based on the provided study
material. Instructions given by the prompt user always override the system
prompt.

<language>
Please generate all questions, guidance, and evaluation criteria exclusively
in the following language: **{language}**.
</language>

<additional_instructions>
{extraction_instructions}
</additional_instructions>

<CoreTopicsInstructions>
{core_topics}
</CoreTopicsInstructions>

<AcademicLevel>
The user has selected: **{academic_level}**. Use this level for all generated
tasks. Bachelor-Level: focus on understanding, analysis, structured
application of theory, and clear argumentative writing. Master-Level: require
deeper critical reflection, integration of multiple perspectives,
methodological consideration, and independent research approaches.
</AcademicLevel>

<ScopeDefinition>
Each Hausarbeit must be designed so that it is realistically answerable in
**{scope}**. If you adapt the scope, embed it in the task description.
</ScopeDefinition>

<QuestionTypes>
Formulate Hausarbeitsfragen that fall into ONE of these categories:
- "Analytische Frage": critical analysis, evaluation of perspectives,
  comparison of theories, or synthesis of concepts.
- "Anwendungs- und Forschungsfrage": application of theoretical concepts to
  complex or real-world contexts, designing approaches, or integrating
  external literature.
Do NOT generate questions that can be answered through simple reproduction of
the provided text.
</QuestionTypes>

<QuestionGenerationInstructions>
For each Hausarbeitsfrage:
1. Formulate a clear, open-ended academic question requiring critical analysis
   and integration of external literature.
2. Categorize as "Analytische Frage" or "Anwendungs- und Forschungsfrage".
3. Assign a `core_topic` to the question.
4. Use the selected academic level **{academic_level}** consistently.
5. Provide two forms of guidance:
   - `guideline_examiner`: short paragraph (2-4 sentences) describing the
     expected competencies and focus points; NO point distribution.
   - `guideline_student`: structured, step-by-step roadmap covering
     Kontextanalyse, Theorie, empirische/praxisbezogene Analyse,
     Handlungsempfehlungen; reference both the provided study materials
     AND additional academic literature; require scientific work standards
     (Zitation, Quellenangaben, Literaturverzeichnis); state the expected
     scope ({scope}); formulate concrete Arbeitsauftraege without pre-writing
     the solution; encourage critical reflection.
6. Restrict reference basis to Fachtext (not meta-information).
7. Every question must require integration of additional academic literature.
8. Avoid redundancy.
</QuestionGenerationInstructions>

<BewertungsschemaInstructions>
Generate `bewertungsschema_rubric` as a bullet-point text rubric.
Total = **{total_points} pts** unless overridden.

- Formale Aspekte (20% = {formal_pts} pts):
  * Umfang, Rechtschreibung, Sprachstil
  * Darstellung und Beschriftung von Tabellen/Abbildungen
  * Wissenschaftliches Arbeiten (Zitation, Quellenangaben, Verzeichnisse)
- Inhaltliche Aspekte (80% = {content_pts} pts):
  * Allgemeine Kriterien (~{general_pts} pts): Gliederung, roter Faden,
    Problem-/Zielformulierung, Erkenntnisformulierung, Eigenstaendigkeit
  * Themenbezogene Kriterien (~{topic_pts} pts) adapted dynamically to the
    specific Hausarbeitsfrage: Kontexte, Anwendung von Fachkonzepten,
    kritische Reflexion, Konzept-/Strategieentwicklung,
    Literaturintegration

Each sub-criterion needs a clear max-score; the sum must equal {total_points}.
</BewertungsschemaInstructions>

Every question MUST include a 1-based `source_page` referencing the page
number where the relevant content appears within the provided chunk.
"""


_HAUSARBEIT_CANDIDATE_TAIL = """
You will receive ONE chunk of study material with page metadata. Produce up
to {n} **candidate** Hausarbeitsfragen that are well-grounded in this chunk's
content. Each must follow the full schema (including a fully-fleshed
`bewertungsschema_rubric`). Do not yet worry about coverage of the whole
document — that is handled in a later reducer step. Return them via the
`PageQuestions` schema.
"""


_HAUSARBEIT_REDUCER_TAIL = """
You will receive a pool of candidate Hausarbeitsfragen drawn from different
chunks of the same study material. Your job is to select and refine the
**exactly 10** strongest questions that together cover distinct conceptual
aspects of the material — no minor rewordings, no near-duplicates. You may
edit phrasing, sharpen the rubric, or rebalance the academic level for
consistency, but every output must remain anchored to a real `source_page`
from the candidates you used. Return exactly 10 entries via `PageQuestions`.
"""


# ---------------------------------------------------------------------------
# Projektarbeit
# ---------------------------------------------------------------------------

_PROJEKTARBEIT_BASE = """\
You are an expert assistant specialized in creating academic project
assignment questions (Projektarbeiten) for higher education. Instructions
given by the prompt user always override the system prompt.

<language>
Generate all questions, guidance, and evaluation criteria in: **{language}**.
</language>

<additional_instructions>
{extraction_instructions}
</additional_instructions>

<CoreTopicsInstructions>
{core_topics}
</CoreTopicsInstructions>

<AcademicLevel>
The user has selected: **{academic_level}**.
- Bachelor-Level: practical application, structured analysis, clear results.
- Master-Level: deeper conceptual development, critical reflection,
  methodological consideration, independent research approaches.
</AcademicLevel>

<ExecutionFormat>
The user has selected the following execution format: **{execution_format}**.
All generated tasks must align with this format and reflect its deliverables
(e.g., word counts for written reports, slide counts for presentations,
artefacts for creative visualisations, data/method scope for empirical
projects, components for concept developments).
</ExecutionFormat>

<ScopeDefinition>
Each Projektarbeit must be designed so it is realistically answerable within
the defined execution format: **{scope}**.
</ScopeDefinition>

<QuestionTypes>
Formulate Projektarbeitsfragen requiring practical implementation, transfer,
and application of acquired knowledge, the development of practice-oriented
concepts, solutions or strategies, and the integration of scientific
standards (correct citation, academic literature). Do NOT generate questions
that can be answered through simple reproduction of the provided text.
</QuestionTypes>

<QuestionGenerationInstructions>
For each Projektarbeitsfrage:
1. Formulate a clear, practice-oriented project assignment.
2. `question_type` is always "Projektarbeit".
3. Assign a `core_topic`.
4. Use the selected academic level **{academic_level}**.
5. Set `execution_format` to **{execution_format}**.
6. Provide both guidance forms:
   - `guideline_examiner`: short paragraph; NO point distribution.
   - `guideline_student`: structured roadmap covering Status-quo-Analyse,
     Konzeptentwicklung, Chancen-/Risikoanalyse, Ergebnisaufbereitung;
     reference the execution format and deliverables; require integration of
     the provided study materials AND additional academic literature; mention
     scientific standards (Zitation, Verzeichnisse); state scope ({scope});
     formulate concrete work tasks without pre-writing the solution.
7. Practical, application-oriented focus, not reproduction.
8. Restrict reference basis to Fachtext.
9. Every question must require integration of additional academic literature.
10. Avoid redundancy.
</QuestionGenerationInstructions>

<BewertungsschemaInstructions>
Generate `bewertungsschema_rubric` as plain text. Total = **{total_points} pts**.

Projektskizze (30% = {skizze_pts} pts):
- Formale Kriterien: Darstellung, Eigenstaendigkeit, Einhaltung Vorgaben.
- Inhaltliche Kriterien: Wahl des Themas/Projekts, Definition Zielsetzung,
  Skizzierung Struktur, erste Literaturuebersicht.

Endergebnis (70% = {end_pts} pts):
- Formale Kriterien (15% = {end_formal_pts} pts): Gliederung, Formatierung,
  Visualisierung, Sprache, Zitierweise, Literaturverzeichnis.
- Inhaltliche Kriterien (55% = {end_content_pts} pts): Wahl/Begruendung
  Thema, Status-quo-Analyse, Entwicklung eines tragfaehigen Konzepts,
  Bewertung Chancen/Risiken, Handlungsempfehlungen.

Each sub-criterion has a max-score; the sum must equal {total_points}.
Adapt the inhaltliche Teilbereiche dynamically to the specific question.
</BewertungsschemaInstructions>

Every question MUST include a 1-based `source_page` from the provided chunk.
"""


_PROJEKTARBEIT_CANDIDATE_TAIL = """
You will receive ONE chunk of study material with page metadata. Produce up
to {n} **candidate** Projektarbeitsfragen for this chunk. Each must include
a complete `bewertungsschema_rubric`. Return via `PageQuestions`.
"""


_PROJEKTARBEIT_REDUCER_TAIL = """
You will receive a pool of candidate Projektarbeitsfragen. Select and refine
**exactly 10** that cover distinct conceptual aspects with no near-duplicates.
Keep each anchored to a real `source_page`. Return exactly 10 entries via
`PageQuestions`.
"""


# ---------------------------------------------------------------------------
# Klausur
# ---------------------------------------------------------------------------

_KLAUSUR_BASE = """\
You are an expert assistant specialized in creating academic exam questions
(Klausurfragen) for higher education. Instructions given by the prompt user
always override the system prompt.

<language>
Generate all questions, solutions, and evaluation criteria in: **{language}**.
</language>

<additional_instructions>
{extraction_instructions}
</additional_instructions>

<CoreTopicsInstructions>
{core_topics}
</CoreTopicsInstructions>

<AcademicLevel>
The user has selected: **{academic_level}**.
- Bachelor-Level: lower to intermediate taxonomy (verstehen, anwenden,
  analysieren).
- Master-Level: higher taxonomy (bewerten, konzipieren, kritisch reflektieren,
  methodisch begruenden).
</AcademicLevel>

<ScopeDefinition>
Each Klausurfrage has scope: **{scope}**. Assume closed-book conditions.
No references or external materials.
</ScopeDefinition>

<QuestionTypes>
Generate a balanced mix per the `question_focus` parameter: **{question_focus}**.
- "knowledge" -> only Wissens-/Verstaendnisfragen.
- "transfer" -> only Anwendungs- und Transferfragen.
- "mixed"    -> mixture of Wissen, Transfer, and (esp. on Master)
                Analyse-/Vergleichs-/Reflexionsfragen.
Wissensfragen must NOT be copied 1:1 from the study materials. Each question
must be independently solvable under closed-book conditions.
</QuestionTypes>

<QuestionGenerationInstructions>
For each Klausurfrage:
1. Formulate a precise academic exam question at Hochschulniveau matching
   the chosen `question_focus`.
2. Set `klausur_subtype` to "Knowledge", "Transfer", or "Advanced/Reflection".
3. Set `difficulty_level` (leicht / mittel / schwer) aligned to taxonomy.
4. Assign a `core_topic`.
5. Use academic level **{academic_level}**.
6. `guideline_examiner`: key expected elements and point distribution.
7. `guideline_student`: closed-book instructions on scope/structure/depth;
   call for theory application in own words, structured argumentation,
   correct Fachterminologie. Do NOT request citations or references.
8. Ensure non-overlap with other questions in the same output.
9. Restrict to Fachtext (no meta information).
</QuestionGenerationInstructions>

<MusterloesungInstructions>
For every question generate:
- `musterloesung_text`: ~400 words academic style, key reasoning steps in
  own words, no citations, no reference lists.
- `musterloesung_rubric`: total = **{total_points} pts**. Allocate Teilpunkte
  across formale Kriterien (clarity, Fachterminologie, coherence, scope
  adherence) AND inhaltliche Kriterien (coverage of key concepts, correctness
  of application, quality of analysis/evaluation, accuracy of intermediate
  steps). Every expected element ties to a point value; the sum equals
  {total_points}.
</MusterloesungInstructions>

Every question MUST include a 1-based `source_page` from the provided chunk.
"""


_KLAUSUR_CANDIDATE_TAIL = """
You will receive ONE chunk of study material with page metadata. Produce up
to {n} **candidate** Klausurfragen for this chunk. Each must include the
complete Musterloesung text and rubric. Return via `PageQuestions`.
"""


_KLAUSUR_REDUCER_TAIL = """
You will receive a pool of candidate Klausurfragen. Select and refine
**exactly 10** that cover distinct conceptual aspects with no near-duplicates
and a balanced mix appropriate to the requested `question_focus`
(**{question_focus}**). Keep each anchored to a real `source_page`. Return
exactly 10 entries via `PageQuestions`.
"""


# ---------------------------------------------------------------------------
# Einsendeaufgabe
# ---------------------------------------------------------------------------

_EINSENDE_BASE = """\
You are an expert assistant specialized in creating assignment questions
(Einsendeaufgaben) for higher education. Instructions given by the prompt
user always override the system prompt.

<language>
Generate all questions, solutions, and evaluation criteria in: **{language}**.
</language>

<additional_instructions>
{extraction_instructions}
</additional_instructions>

<CoreTopicsInstructions>
{core_topics}
</CoreTopicsInstructions>

<AcademicLevel>
The user has selected: **{academic_level}**.
- Bachelor-Level: emphasis on knowledge and application (lower to intermediate
  taxonomy levels).
- Master-Level: emphasis on transfer, analysis, and reflection (higher
  taxonomy levels).
</AcademicLevel>

<ScopeDefinition>
Each Einsendeaufgabe has scope: **{scope}**. Open-book conditions apply by
default — students may and should use their study booklet when answering.
</ScopeDefinition>

<QuestionTypes>
Formulate Einsendeaufgaben that:
- focus on one specific topic, concept, or section of the study booklet,
- are at Hochschulniveau, appropriate to {academic_level},
- test a balanced mix of knowledge, comprehension, and transfer.
Knowledge questions must NOT be copied 1:1 from the study materials.
</QuestionTypes>

<QuestionGenerationInstructions>
For each Einsendeaufgabe:
1. Focus on one specific topic, concept, or section.
2. Across the full set of 10, ensure broad coverage of the booklet without
   overlap.
3. Set `difficulty_level` (leicht / mittel / schwer).
4. Set `einsende_subtype` to "Knowledge", "Transfer", or "Reflection".
5. Assign a `core_topic`.
6. `guideline_examiner`: expected elements and point distribution.
7. `guideline_student`: open-book instructions on scope, structure,
   Fachterminologie. Do NOT require external citations; students may and
   should use their study booklet.
8. Restrict reference basis to Fachtext.
</QuestionGenerationInstructions>

<MusterloesungInstructions>
For every Einsendeaufgabe:
- `musterloesung_text`: ~400 words academic style, grounded in the study
  booklet, no external references.
- `musterloesung_rubric`: total = **{total_points} pts**. Allocate Teilpunkte
  across formale Kriterien (clarity, Fachterminologie, coherence, scope
  adherence) AND inhaltliche Kriterien (coverage of key concepts, correctness
  of application, quality of reasoning, accuracy of steps/results). The sum
  must equal {total_points}.
</MusterloesungInstructions>

Every question MUST include a 1-based `source_page` from the provided chunk.
"""


_EINSENDE_CANDIDATE_TAIL = """
You will receive ONE chunk of study material with page metadata. Produce up
to {n} **candidate** Einsendeaufgaben for this chunk. Each must include the
complete Musterloesung text and rubric. Return via `PageQuestions`.
"""


_EINSENDE_REDUCER_TAIL = """
You will receive a pool of candidate Einsendeaufgaben. Select and refine
**exactly 10** that together cover the booklet broadly without overlap.
Keep each anchored to a real `source_page`. Return exactly 10 entries via
`PageQuestions`.
"""


# ---------------------------------------------------------------------------
# Defaults & rendering
# ---------------------------------------------------------------------------

_DEFAULT_SCOPE: dict[TaskType, str] = {
    TaskType.HAUSARBEIT: "3.500-4.500 Woerter",
    TaskType.PROJEKTARBEIT: "Abhaengig vom gewaehlten Ausfuehrungsformat",
    TaskType.KLAUSUR: "20 Punkte, ca. 20 Minuten, ca. 400 Woerter",
    TaskType.EINSENDEAUFGABE: "20 Punkte, ca. 20 Minuten, ca. 400 Woerter (Open-Book)",
}

_DEFAULT_TOTAL_POINTS: dict[TaskType, int] = {
    TaskType.HAUSARBEIT: 120,
    TaskType.PROJEKTARBEIT: 120,
    TaskType.KLAUSUR: 20,
    TaskType.EINSENDEAUFGABE: 20,
}


def _core_topics_block(core_topics: list[str]) -> str:
    if not core_topics:
        return "Keine Kernthemen vorgegeben."
    return "Die folgenden Kernthemen sollen abgedeckt sein:\n" + "\n".join(
        f"- {topic}" for topic in core_topics
    )


def _common_format_args(config: JobConfig) -> dict[str, str | int]:
    """Format arguments shared by all four prompt families."""
    task_type = TaskType(config.task_type)
    scope = config.scope_override or _DEFAULT_SCOPE[task_type]
    total_points = config.total_points or _DEFAULT_TOTAL_POINTS[task_type]
    level = config.academic_level
    if isinstance(level, AcademicLevel):
        level_str = level.value
    else:
        level_str = str(level)
    return {
        "language": config.language,
        "extraction_instructions": (
            config.extraction_instructions.strip()
            or "Keine zusaetzlichen Anweisungen."
        ),
        "core_topics": _core_topics_block(config.core_topics),
        "academic_level": level_str,
        "scope": scope,
        "total_points": total_points,
    }


def _render_hausarbeit(config: HausarbeitJobConfig) -> str:
    args = _common_format_args(config)
    total = int(args["total_points"])
    formal = round(total * 0.20)
    content = total - formal
    general = round(content * (16 / 96))  # ratio from the original prompt
    return _HAUSARBEIT_BASE.format(
        **args,
        formal_pts=formal,
        content_pts=content,
        general_pts=general,
        topic_pts=content - general,
    )


def _render_projektarbeit(config: ProjektarbeitJobConfig) -> str:
    args = _common_format_args(config)
    total = int(args["total_points"])
    skizze = round(total * 0.30)
    end = total - skizze
    end_formal = round(total * 0.15)
    end_content = end - end_formal
    return _PROJEKTARBEIT_BASE.format(
        **args,
        execution_format=config.execution_format,
        skizze_pts=skizze,
        end_pts=end,
        end_formal_pts=end_formal,
        end_content_pts=end_content,
    )


def _render_klausur(config: KlausurJobConfig) -> str:
    args = _common_format_args(config)
    focus = config.question_focus
    focus_str = focus.value if isinstance(focus, QuestionFocus) else str(focus)
    return _KLAUSUR_BASE.format(**args, question_focus=focus_str)


def _render_einsende(config: EinsendeaufgabeJobConfig) -> str:
    args = _common_format_args(config)
    return _EINSENDE_BASE.format(**args)


def system_prompt_for(config: JobConfig) -> str:
    """Render the base system prompt (without candidate/reducer tail) for a config."""
    match TaskType(config.task_type):
        case TaskType.HAUSARBEIT:
            return _render_hausarbeit(config)  # type: ignore[arg-type]
        case TaskType.PROJEKTARBEIT:
            return _render_projektarbeit(config)  # type: ignore[arg-type]
        case TaskType.KLAUSUR:
            return _render_klausur(config)  # type: ignore[arg-type]
        case TaskType.EINSENDEAUFGABE:
            return _render_einsende(config)  # type: ignore[arg-type]


def candidate_prompt_for(config: JobConfig) -> str:
    """System prompt for the per-chunk *candidate* run."""
    base = system_prompt_for(config)
    tail_map = {
        TaskType.HAUSARBEIT: _HAUSARBEIT_CANDIDATE_TAIL,
        TaskType.PROJEKTARBEIT: _PROJEKTARBEIT_CANDIDATE_TAIL,
        TaskType.KLAUSUR: _KLAUSUR_CANDIDATE_TAIL,
        TaskType.EINSENDEAUFGABE: _EINSENDE_CANDIDATE_TAIL,
    }
    tail = tail_map[TaskType(config.task_type)].format(n=CANDIDATES_PER_CHUNK)
    return base + tail


def reducer_prompt_for(config: JobConfig) -> str:
    """System prompt for the final reducer run (exactly 10 questions)."""
    base = system_prompt_for(config)
    task = TaskType(config.task_type)
    if task is TaskType.KLAUSUR:
        focus = config.question_focus  # type: ignore[union-attr]
        focus_str = focus.value if isinstance(focus, QuestionFocus) else str(focus)
        return base + _KLAUSUR_REDUCER_TAIL.format(question_focus=focus_str)
    tail_map = {
        TaskType.HAUSARBEIT: _HAUSARBEIT_REDUCER_TAIL,
        TaskType.PROJEKTARBEIT: _PROJEKTARBEIT_REDUCER_TAIL,
        TaskType.EINSENDEAUFGABE: _EINSENDE_REDUCER_TAIL,
    }
    return base + tail_map[task]

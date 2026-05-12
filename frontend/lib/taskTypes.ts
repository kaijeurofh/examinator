export type TaskType = "hausarbeit" | "projektarbeit" | "klausur" | "einsendeaufgabe";

export interface TaskTypeMeta {
  id: TaskType;
  label: string;
  shortLabel: string;
  description: string;
  defaultScope: string;
}

export const TASK_TYPES: ReadonlyArray<TaskTypeMeta> = [
  {
    id: "hausarbeit",
    label: "Hausarbeitsfragen",
    shortLabel: "Hausarbeit",
    description:
      "Wissenschaftliche Hausarbeitsthemen mit Analytischen oder Anwendungs-/Forschungsfragen, Bewertungsschema und Bearbeitungshinweisen.",
    defaultScope: "3.500-4.500 Woerter",
  },
  {
    id: "projektarbeit",
    label: "Projektarbeitsfragen",
    shortLabel: "Projektarbeit",
    description:
      "Praxisorientierte Projektaufgaben mit waehlbarem Ausfuehrungsformat (Bericht, Praesentation, empirisch, Konzept).",
    defaultScope: "Abhaengig vom Ausfuehrungsformat",
  },
  {
    id: "klausur",
    label: "Klausurfragen",
    shortLabel: "Klausur",
    description:
      "Closed-Book Klausurfragen (Wissen/Transfer/Reflexion) inklusive Musterloesung und Bewertungsrubrik.",
    defaultScope: "20 Punkte, ca. 20 Minuten, ca. 400 Woerter",
  },
  {
    id: "einsendeaufgabe",
    label: "Einsendeaufgaben",
    shortLabel: "Einsende",
    description:
      "Open-Book Einsendeaufgaben fuer ein gesamtes Studienheft mit Musterloesung und Bewertungsrubrik.",
    defaultScope: "20 Punkte, ca. 20 Minuten, ca. 400 Woerter (Open-Book)",
  },
];

export function getTaskMeta(id: string): TaskTypeMeta | undefined {
  return TASK_TYPES.find((t) => t.id === id);
}

export type AcademicLevel = "Bachelor" | "Master";
export type QuestionFocus = "knowledge" | "transfer" | "mixed";

export interface BaseJobConfig {
  task_type: TaskType;
  language: string;
  extraction_instructions: string;
  core_topics: string[];
  academic_level: AcademicLevel;
  scope_override?: string | null;
  total_points?: number | null;
}

export interface HausarbeitJobConfig extends BaseJobConfig {
  task_type: "hausarbeit";
}

export interface ProjektarbeitJobConfig extends BaseJobConfig {
  task_type: "projektarbeit";
  execution_format: string;
}

export interface KlausurJobConfig extends BaseJobConfig {
  task_type: "klausur";
  question_focus: QuestionFocus;
}

export interface EinsendeaufgabeJobConfig extends BaseJobConfig {
  task_type: "einsendeaufgabe";
}

export type JobConfig =
  | HausarbeitJobConfig
  | ProjektarbeitJobConfig
  | KlausurJobConfig
  | EinsendeaufgabeJobConfig;

"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Dropzone } from "@/components/Dropzone";
import { createJob } from "@/lib/api";
import type {
  AcademicLevel,
  JobConfig,
  QuestionFocus,
  TaskType,
} from "@/lib/taskTypes";

interface NewJobFormProps {
  taskType: TaskType;
  defaultScope: string;
}

type InputMode = "pdf" | "text";

export function NewJobForm({ taskType, defaultScope }: NewJobFormProps) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Common fields.
  const [language, setLanguage] = useState("Deutsch");
  const [academicLevel, setAcademicLevel] = useState<AcademicLevel>("Bachelor");
  const [coreTopicsText, setCoreTopicsText] = useState("");
  const [extractionInstructions, setExtractionInstructions] = useState("");
  const [scopeOverride, setScopeOverride] = useState("");
  const [totalPoints, setTotalPoints] = useState("");

  // Task-type-specific.
  const [questionFocus, setQuestionFocus] = useState<QuestionFocus>("mixed");
  const [executionFormat, setExecutionFormat] = useState(
    "Schriftlicher Projektbericht (3.500-4.500 Woerter)"
  );

  // Input.
  const [inputMode, setInputMode] = useState<InputMode>("pdf");
  const [pdf, setPdf] = useState<File | null>(null);
  const [text, setText] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);

    if (inputMode === "pdf" && !pdf) {
      setError("Bitte PDF auswaehlen oder zur Texteingabe wechseln.");
      return;
    }
    if (inputMode === "text" && text.trim().length < 50) {
      setError("Bitte mindestens 50 Zeichen Studientext einfuegen.");
      return;
    }

    const coreTopics = coreTopicsText
      .split(/[\n,]+/)
      .map((t) => t.trim())
      .filter((t) => t.length > 0);

    const base = {
      language,
      extraction_instructions: extractionInstructions,
      core_topics: coreTopics,
      academic_level: academicLevel,
      scope_override: scopeOverride.trim() ? scopeOverride.trim() : null,
      total_points: totalPoints ? Number(totalPoints) : null,
    };

    let config: JobConfig;
    switch (taskType) {
      case "hausarbeit":
        config = { task_type: "hausarbeit", ...base };
        break;
      case "projektarbeit":
        config = {
          task_type: "projektarbeit",
          ...base,
          execution_format: executionFormat,
        };
        break;
      case "klausur":
        config = {
          task_type: "klausur",
          ...base,
          question_focus: questionFocus,
        };
        break;
      case "einsendeaufgabe":
        config = { task_type: "einsendeaufgabe", ...base };
        break;
    }

    setSubmitting(true);
    try {
      const { job_id } = await createJob({
        config,
        pdf: inputMode === "pdf" ? pdf : null,
        text: inputMode === "text" ? text : null,
      });
      router.push(`/jobs/${job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Card title="Studienmaterial">
        <div className="flex gap-2">
          <Tab
            active={inputMode === "pdf"}
            onClick={() => setInputMode("pdf")}
            label="PDF hochladen"
          />
          <Tab
            active={inputMode === "text"}
            onClick={() => setInputMode("text")}
            label="Text einfuegen"
          />
        </div>
        <div className="mt-4">
          {inputMode === "pdf" ? (
            <Dropzone value={pdf} onChange={setPdf} maxMb={20} />
          ) : (
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Studientext hier einfuegen (mindestens 50 Zeichen)..."
              className="min-h-[200px] w-full rounded-xl border border-slate-300 bg-white p-3 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          )}
        </div>
      </Card>

      <Card title="Allgemeine Parameter">
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Sprache">
            <input
              type="text"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className={inputClass}
            />
          </Field>
          <Field label="Akademisches Niveau">
            <div className="flex gap-3">
              {(["Bachelor", "Master"] as AcademicLevel[]).map((lvl) => (
                <label
                  key={lvl}
                  className={`flex-1 cursor-pointer rounded-xl border px-4 py-2 text-center text-sm ${
                    academicLevel === lvl
                      ? "border-brand-500 bg-brand-50 text-brand-800"
                      : "border-slate-300 bg-white"
                  }`}
                >
                  <input
                    type="radio"
                    name="level"
                    value={lvl}
                    checked={academicLevel === lvl}
                    onChange={() => setAcademicLevel(lvl)}
                    className="hidden"
                  />
                  {lvl}
                </label>
              ))}
            </div>
          </Field>
        </div>

        <Field label="Kernthemen (Komma- oder zeilengetrennt)">
          <textarea
            value={coreTopicsText}
            onChange={(e) => setCoreTopicsText(e.target.value)}
            placeholder="z. B. Marketing-Mix, Markenstrategie, Konsumentenverhalten"
            className="min-h-[80px] w-full rounded-xl border border-slate-300 bg-white p-3 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </Field>

        <Field label="Zusatzanweisungen (optional)">
          <textarea
            value={extractionInstructions}
            onChange={(e) => setExtractionInstructions(e.target.value)}
            placeholder="z. B. Schwerpunkt auf Kapitel 3, oder bestimmte Theorien hervorheben"
            className="min-h-[80px] w-full rounded-xl border border-slate-300 bg-white p-3 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </Field>

        <div className="grid gap-4 md:grid-cols-2">
          <Field label={`Umfang (Default: ${defaultScope})`}>
            <input
              type="text"
              value={scopeOverride}
              onChange={(e) => setScopeOverride(e.target.value)}
              placeholder="leer = Default verwenden"
              className={inputClass}
            />
          </Field>
          <Field label="Gesamtpunkte (optional)">
            <input
              type="number"
              value={totalPoints}
              onChange={(e) => setTotalPoints(e.target.value)}
              placeholder="z. B. 120 / 20"
              min={1}
              className={inputClass}
            />
          </Field>
        </div>
      </Card>

      {taskType === "klausur" && (
        <Card title="Klausur-spezifisch">
          <Field label="Fragefokus">
            <div className="flex flex-wrap gap-2">
              {(["mixed", "knowledge", "transfer"] as QuestionFocus[]).map((f) => (
                <label
                  key={f}
                  className={`cursor-pointer rounded-full border px-4 py-1.5 text-sm ${
                    questionFocus === f
                      ? "border-brand-500 bg-brand-50 text-brand-800"
                      : "border-slate-300 bg-white"
                  }`}
                >
                  <input
                    type="radio"
                    name="focus"
                    value={f}
                    checked={questionFocus === f}
                    onChange={() => setQuestionFocus(f)}
                    className="hidden"
                  />
                  {f === "mixed"
                    ? "Mischung (Default)"
                    : f === "knowledge"
                      ? "Nur Wissen / Verstaendnis"
                      : "Nur Anwendung / Transfer"}
                </label>
              ))}
            </div>
          </Field>
        </Card>
      )}

      {taskType === "projektarbeit" && (
        <Card title="Projektarbeit-spezifisch">
          <Field label="Ausfuehrungsformat">
            <select
              value={executionFormat}
              onChange={(e) => setExecutionFormat(e.target.value)}
              className={inputClass}
            >
              <option>Schriftlicher Projektbericht (3.500-4.500 Woerter)</option>
              <option>Schriftlicher Projektbericht (2.500-3.500 Woerter)</option>
              <option>Praesentation (max. 20 Folien) mit Erlaeuterungstext (2.000-3.000 Woerter)</option>
              <option>Kreative Visualisierung mit Erlaeuterungstext/Audio/Video</option>
              <option>Empirischer Projektbericht (Datenerhebung, Auswertung, Interpretation)</option>
              <option>Konzeptentwicklung (Beratung, Praevention, Intervention, Training)</option>
            </select>
          </Field>
        </Card>
      )}

      {error && (
        <div className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex items-center justify-end gap-3">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-xl bg-brand-700 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {submitting ? "Job wird gestartet ..." : "10 Aufgaben generieren"}
        </button>
      </div>
    </form>
  );
}

const inputClass =
  "w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";

function Card({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </h2>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      {children}
    </label>
  );
}

function Tab({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
        active
          ? "bg-brand-700 text-white"
          : "bg-slate-100 text-slate-600 hover:bg-slate-200"
      }`}
    >
      {label}
    </button>
  );
}

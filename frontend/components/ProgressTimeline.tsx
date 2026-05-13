"use client";

import { useEffect, useState } from "react";
import type { ProgressEventData } from "@/lib/api";

export interface TimedEvent {
  ev: ProgressEventData;
  receivedAt: number;
}

type JobStatus = "queued" | "running" | "done" | "error";

const STAGE_INFO: Record<string, { title: string; description: string }> = {
  queued: {
    title: "In der Warteschlange",
    description: "Job wartet auf einen freien Slot.",
  },
  parsing: {
    title: "Eingabe wird gelesen",
    description: "PDF/Text wird in Seiten zerlegt.",
  },
  chunking: {
    title: "Inhalte werden aufgeteilt",
    description: "Material wird in überlappende Abschnitte zerlegt.",
  },
  chunk_started: {
    title: "Fragen werden erzeugt",
    description:
      "Das LLM generiert Kandidatenfragen für jeden Abschnitt – das ist üblicherweise der längste Schritt.",
  },
  chunk_done: {
    title: "Abschnitt fertig",
    description: "Kandidatenfragen für diesen Abschnitt liegen vor.",
  },
  reducing: {
    title: "Beste Fragen werden ausgewählt",
    description:
      "Aus dem Kandidatenpool werden 10 finale, sich nicht überschneidende Fragen gewählt.",
  },
  done: {
    title: "Fertig",
    description: "Alle Fragen wurden generiert.",
  },
  error: {
    title: "Fehler",
    description: "Job wurde abgebrochen.",
  },
};

// Reihenfolge der sichtbaren Hauptschritte. ``chunk_done`` ist nur ein
// Sub-Tick innerhalb von ``chunk_started`` und zählt nicht als eigener Schritt.
const MAIN_STAGES = [
  "parsing",
  "chunking",
  "chunk_started",
  "reducing",
  "done",
] as const;

// Defaults für die initiale Dauerprognose. Bewusst breite Spanne, weil die
// echte Laufzeit stark vom verwendeten LLM abhängt (siehe benchmark.md:
// 60 s – 280 s Wall-clock je Modell für einen einzelnen Chunk).
const DEFAULT_CHUNK_SEC_MIN = 30;
const DEFAULT_CHUNK_SEC_MAX = 90;
const REDUCER_SEC_MIN = 20;
const REDUCER_SEC_MAX = 60;
const REDUCER_SEC_EST = 40;

function formatDuration(totalSeconds: number): string {
  const safe = Number.isFinite(totalSeconds) && totalSeconds > 0 ? totalSeconds : 0;
  const s = Math.round(safe);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}

function formatRange(minSec: number, maxSec: number): string {
  if (maxSec < 90) {
    return `${Math.round(minSec)}–${Math.round(maxSec)} s`;
  }
  const minMin = minSec / 60;
  const maxMin = maxSec / 60;
  const fmt = (v: number) => (v >= 10 ? Math.round(v).toString() : v.toFixed(1));
  return `${fmt(minMin)}–${fmt(maxMin)} Min`;
}

function formatDelta(seconds: number): string {
  if (seconds < 10) return `+${seconds.toFixed(1)} s`;
  return `+${Math.round(seconds)} s`;
}

interface DerivedState {
  currentStage: keyof typeof STAGE_INFO | string;
  stepNumber: number;
  totalSteps: number;
  totalChunks: number;
  chunksDone: number;
  firstChunkStartedAt: number | undefined;
}

function deriveState(events: TimedEvent[], status: JobStatus): DerivedState {
  const totalChunks =
    events.find((e) => e.ev.stage === "chunking")?.ev.total ??
    events.find((e) => e.ev.stage === "chunk_started")?.ev.total ??
    0;
  const chunksDone = events.filter((e) => e.ev.stage === "chunk_done").length;
  const firstChunkStartedAt = events.find((e) => e.ev.stage === "chunk_started")
    ?.receivedAt;

  const latest = events[events.length - 1]?.ev;
  let currentStage: string;
  if (status === "done") {
    currentStage = "done";
  } else if (status === "error") {
    currentStage = "error";
  } else if (!latest) {
    currentStage = "queued";
  } else if (latest.stage === "chunk_done") {
    // Zwischen zwei Chunks: konzeptionell weiterhin im "chunk_started"-Schritt.
    currentStage = "chunk_started";
  } else {
    currentStage = latest.stage;
  }

  const idx = (MAIN_STAGES as readonly string[]).indexOf(currentStage);
  const stepNumber = idx >= 0 ? idx + 1 : 0;
  return {
    currentStage,
    stepNumber,
    totalSteps: MAIN_STAGES.length,
    totalChunks,
    chunksDone,
    firstChunkStartedAt,
  };
}

interface EtaInfo {
  text: string;
  tone: "estimate" | "measured";
}

function computeEta(
  derived: DerivedState,
  status: JobStatus,
  now: number,
): EtaInfo | null {
  if (status !== "running") return null;
  const { currentStage, totalChunks, chunksDone, firstChunkStartedAt } = derived;

  if (currentStage === "parsing" || currentStage === "chunking" || currentStage === "queued") {
    return {
      text: "Erwartete Gesamtdauer: 2–8 Minuten (abhängig vom Modell und Materialumfang).",
      tone: "estimate",
    };
  }

  if (currentStage === "chunk_started" && totalChunks > 0) {
    if (chunksDone > 0 && firstChunkStartedAt !== undefined) {
      const measuredAvg = (now - firstChunkStartedAt) / 1000 / chunksDone;
      const remaining = Math.max(
        0,
        (totalChunks - chunksDone) * measuredAvg + REDUCER_SEC_EST,
      );
      return {
        text: `Noch ca. ${formatDuration(remaining)} (gemessen aus bisherigen Abschnitten).`,
        tone: "measured",
      };
    }
    const minEta = totalChunks * DEFAULT_CHUNK_SEC_MIN + REDUCER_SEC_MIN;
    const maxEta = totalChunks * DEFAULT_CHUNK_SEC_MAX + REDUCER_SEC_MAX;
    return {
      text: `Erwartete Restdauer: ~${formatRange(minEta, maxEta)} (abhängig vom Modell).`,
      tone: "estimate",
    };
  }

  if (currentStage === "reducing") {
    return {
      text: `Reduktion läuft, üblicherweise ${formatRange(REDUCER_SEC_MIN, REDUCER_SEC_MAX)}.`,
      tone: "estimate",
    };
  }

  return null;
}

export function ProgressTimeline({
  events,
  status,
  startedAt,
}: {
  events: TimedEvent[];
  status: JobStatus;
  startedAt: number;
}) {
  // Tickender Timer für Stoppuhr und Live-ETA. Nur aktiv solange der Job läuft.
  const [now, setNow] = useState<number>(() => Date.now());
  useEffect(() => {
    if (status !== "running" && status !== "queued") {
      setNow(Date.now());
      return;
    }
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [status]);

  const derived = deriveState(events, status);
  const info = STAGE_INFO[derived.currentStage] ?? {
    title: derived.currentStage,
    description: "",
  };

  const lastEventAt = events[events.length - 1]?.receivedAt;
  const elapsedSec =
    status === "running" || status === "queued"
      ? (now - startedAt) / 1000
      : ((lastEventAt ?? now) - startedAt) / 1000;

  const eta = computeEta(derived, status, now);

  const hasProgressBar =
    derived.currentStage === "chunk_started" && derived.totalChunks > 0;
  const progressPct = hasProgressBar
    ? Math.min(100, (derived.chunksDone / derived.totalChunks) * 100)
    : 0;

  const latestMessage = events[events.length - 1]?.ev.message;

  return (
    <div className="space-y-4">
      {(status === "running" || status === "queued") && (
        <LiveCard
          stepNumber={derived.stepNumber}
          totalSteps={derived.totalSteps}
          title={info.title}
          description={info.description}
          latestMessage={latestMessage}
          elapsedSec={elapsedSec}
          hasProgress={hasProgressBar}
          progressCurrent={derived.chunksDone}
          progressTotal={derived.totalChunks}
          progressPct={progressPct}
          eta={eta}
          empty={events.length === 0}
        />
      )}
      {status === "done" && (
        <DoneCard elapsedSec={elapsedSec} />
      )}
      {status === "error" && <ErrorCard elapsedSec={elapsedSec} />}

      <ol className="space-y-2">
        {events.map((te, idx) => {
          const ev = te.ev;
          const prev = events[idx - 1];
          const deltaSec = prev ? (te.receivedAt - prev.receivedAt) / 1000 : 0;
          const isLast = idx === events.length - 1;
          const isRunning =
            (status === "running" || status === "queued") && isLast;
          const stageInfo = STAGE_INFO[ev.stage];
          return (
            <li
              key={`${te.receivedAt}-${idx}`}
              className={`flex items-start gap-3 rounded-xl border px-3 py-2 text-sm transition ${
                ev.stage === "error"
                  ? "border-red-300 bg-red-50 text-red-700"
                  : ev.stage === "done"
                    ? "border-emerald-300 bg-emerald-50 text-emerald-800"
                    : isRunning
                      ? "border-brand-400 bg-brand-50 text-slate-800"
                      : "border-slate-200 bg-white text-slate-700"
              }`}
            >
              <span
                className={`mt-1.5 inline-block h-2 w-2 shrink-0 rounded-full ${
                  ev.stage === "error"
                    ? "bg-red-500"
                    : ev.stage === "done"
                      ? "bg-emerald-500"
                      : isRunning
                        ? "animate-pulse bg-brand-500"
                        : "bg-brand-500"
                }`}
                aria-hidden
              />
              <div className="flex-1">
                <p className="font-medium text-slate-800">
                  {stageInfo?.title ?? ev.stage}
                  {ev.total && ev.total > 0 && ev.current !== undefined ? (
                    <span className="ml-2 text-xs text-slate-500">
                      {ev.current}/{ev.total}
                    </span>
                  ) : null}
                  {deltaSec >= 0.1 && idx > 0 && (
                    <span className="ml-2 text-xs text-slate-400">
                      {formatDelta(deltaSec)}
                    </span>
                  )}
                </p>
                {ev.message && (
                  <p className="text-xs text-slate-500">{ev.message}</p>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function LiveCard(props: {
  stepNumber: number;
  totalSteps: number;
  title: string;
  description: string;
  latestMessage: string | undefined;
  elapsedSec: number;
  hasProgress: boolean;
  progressCurrent: number;
  progressTotal: number;
  progressPct: number;
  eta: EtaInfo | null;
  empty: boolean;
}) {
  return (
    <div className="rounded-2xl border border-brand-300 bg-brand-50 p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <Spinner />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
              {props.stepNumber > 0
                ? `Schritt ${props.stepNumber} von ${props.totalSteps}`
                : "Initialisierung"}
            </p>
            <p
              className="font-mono text-xs text-slate-500"
              title="Bisherige Gesamtdauer"
            >
              {formatDuration(props.elapsedSec)}
            </p>
          </div>
          <h3 className="mt-1 text-base font-semibold text-slate-900">
            {props.title}
          </h3>
          <p className="text-sm text-slate-600">{props.description}</p>
          {props.latestMessage && (
            <p className="mt-1 text-xs text-slate-500">{props.latestMessage}</p>
          )}
          {props.empty && (
            <p className="mt-1 text-xs text-slate-500">
              Verbindung zum Server wird aufgebaut …
            </p>
          )}
        </div>
      </div>

      {props.hasProgress && (
        <div className="mt-3">
          <div className="mb-1 flex items-center justify-between text-xs text-slate-600">
            <span>
              {props.progressCurrent}/{props.progressTotal} Abschnitte fertig
            </span>
            <span className="font-mono">
              {Math.round(props.progressPct)} %
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-white">
            <div
              className="h-full rounded-full bg-brand-500 transition-all duration-500"
              style={{ width: `${props.progressPct}%` }}
            />
          </div>
        </div>
      )}

      {props.eta && (
        <p
          className={`mt-3 text-xs ${
            props.eta.tone === "measured"
              ? "font-medium text-brand-800"
              : "text-slate-600"
          }`}
        >
          {props.eta.text}
        </p>
      )}
    </div>
  );
}

function DoneCard({ elapsedSec }: { elapsedSec: number }) {
  return (
    <div className="rounded-2xl border border-emerald-300 bg-emerald-50 p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
        Fertig
      </p>
      <p className="mt-1 text-base font-semibold text-emerald-900">
        Alle Fragen wurden generiert.
      </p>
      <p className="mt-1 text-xs text-emerald-800">
        Gesamtdauer: {formatDuration(elapsedSec)}
      </p>
    </div>
  );
}

function ErrorCard({ elapsedSec }: { elapsedSec: number }) {
  return (
    <div className="rounded-2xl border border-red-300 bg-red-50 p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-red-700">
        Abgebrochen
      </p>
      <p className="mt-1 text-base font-semibold text-red-900">
        Job konnte nicht abgeschlossen werden.
      </p>
      <p className="mt-1 text-xs text-red-800">
        Laufzeit bis zum Abbruch: {formatDuration(elapsedSec)}
      </p>
    </div>
  );
}

function Spinner() {
  return (
    <span
      className="mt-1 inline-block h-5 w-5 shrink-0 animate-spin rounded-full border-2 border-brand-200 border-t-brand-700"
      aria-label="lädt"
      role="status"
    />
  );
}

export function currentStageTitle(
  events: TimedEvent[],
  status: JobStatus,
): string {
  const { currentStage } = deriveState(events, status);
  return STAGE_INFO[currentStage]?.title ?? currentStage;
}

"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ProgressTimeline,
  currentStageTitle,
  type TimedEvent,
} from "@/components/ProgressTimeline";
import { QuestionCard } from "@/components/QuestionCard";
import {
  eventStreamUrl,
  excelDownloadUrl,
  getJob,
  type JobSnapshot,
  type ProgressEventData,
} from "@/lib/api";

type Status = JobSnapshot["status"];

const HEADLINES: Record<Status, string> = {
  queued: "Job wird vorbereitet …",
  running: "Fragen werden generiert",
  done: "Fragen sind fertig",
  error: "Job fehlgeschlagen",
};

export function JobView({ jobId }: { jobId: string }) {
  const [events, setEvents] = useState<TimedEvent[]>([]);
  const [status, setStatus] = useState<Status>("running");
  const [snapshot, setSnapshot] = useState<JobSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Startzeitpunkt der Anzeige für die Stoppuhr / ETA. Wird einmal beim
  // Mount fixiert und nicht durch Reconnects/Re-Renders verschoben.
  const startedAt = useMemo(() => Date.now(), []);

  useEffect(() => {
    let cancelled = false;
    const url = eventStreamUrl(jobId);
    const source = new EventSource(url);

    const onEvent = (ev: MessageEvent<string>) => {
      try {
        const data = JSON.parse(ev.data) as ProgressEventData;
        if (cancelled) return;
        const timed: TimedEvent = { ev: data, receivedAt: Date.now() };
        setEvents((prev) => [...prev, timed]);
        if (data.stage === "done") {
          setStatus("done");
          source.close();
          getJob(jobId)
            .then((s) => {
              if (!cancelled) setSnapshot(s);
            })
            .catch((err: unknown) => {
              if (!cancelled)
                setError(err instanceof Error ? err.message : String(err));
            });
        } else if (data.stage === "error") {
          setStatus("error");
          setError(data.message ?? "Unbekannter Fehler.");
          source.close();
        }
      } catch {
        // Ignore malformed payloads — heartbeats may include comment lines.
      }
    };

    const stages = [
      "queued",
      "parsing",
      "chunking",
      "chunk_started",
      "chunk_done",
      "reducing",
      "done",
      "error",
    ];
    for (const stage of stages) {
      source.addEventListener(stage, onEvent as EventListener);
    }

    source.onerror = () => {
      if (cancelled) return;
      if (status === "running") {
        setError("Verbindung zum Server unterbrochen.");
        setStatus("error");
      }
      source.close();
    };

    return () => {
      cancelled = true;
      source.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  const stageSubtitle =
    status === "running" || status === "queued"
      ? currentStageTitle(events, status)
      : null;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-brand-500">
            Job {jobId.slice(0, 8)}
          </p>
          <h1 className="text-2xl font-semibold text-slate-900">
            {HEADLINES[status]}
          </h1>
          {stageSubtitle && (
            <p className="mt-1 text-sm text-slate-600">
              Aktuell: {stageSubtitle}
            </p>
          )}
        </div>
        <Link
          href="/"
          className="text-sm text-slate-600 hover:text-brand-700"
        >
          Neuer Job
        </Link>
      </div>

      <section className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Fortschritt
        </h2>
        <ProgressTimeline
          events={events}
          status={status}
          startedAt={startedAt}
        />
        {error && (
          <p className="mt-3 rounded-xl border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
      </section>

      {snapshot?.result && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900">
              {snapshot.result.questions.length} Fragen generiert
            </h2>
            <a
              href={excelDownloadUrl(jobId)}
              className="rounded-xl bg-brand-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-800"
            >
              Excel herunterladen
            </a>
          </div>
          <div className="space-y-3">
            {snapshot.result.questions.map((qa, idx) => (
              <QuestionCard key={idx} qa={qa} index={idx} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

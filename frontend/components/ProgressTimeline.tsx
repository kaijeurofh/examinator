import type { ProgressEventData } from "@/lib/api";

const STAGE_LABELS: Record<string, string> = {
  queued: "In der Warteschlange",
  parsing: "Eingabe wird geparst",
  chunking: "Chunks erzeugt",
  chunk_started: "Chunk gestartet",
  chunk_done: "Chunk fertig",
  reducing: "Reduktion auf 10 Fragen",
  done: "Fertig",
  error: "Fehler",
};

export function ProgressTimeline({
  events,
  status,
}: {
  events: ProgressEventData[];
  status: "queued" | "running" | "done" | "error";
}) {
  return (
    <ol className="space-y-2">
      {events.map((ev, idx) => (
        <li
          key={idx}
          className={`flex items-start gap-3 rounded-xl border px-3 py-2 text-sm ${
            ev.stage === "error"
              ? "border-red-300 bg-red-50 text-red-700"
              : ev.stage === "done"
                ? "border-emerald-300 bg-emerald-50 text-emerald-800"
                : "border-slate-200 bg-white text-slate-700"
          }`}
        >
          <span
            className={`mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full ${
              ev.stage === "error"
                ? "bg-red-500"
                : ev.stage === "done"
                  ? "bg-emerald-500"
                  : "bg-brand-500"
            }`}
            aria-hidden
          />
          <div className="flex-1">
            <p className="font-medium text-slate-800">
              {STAGE_LABELS[ev.stage] ?? ev.stage}
              {ev.total && ev.total > 0 && ev.current !== undefined ? (
                <span className="ml-2 text-xs text-slate-500">
                  {ev.current}/{ev.total}
                </span>
              ) : null}
            </p>
            {ev.message && (
              <p className="text-xs text-slate-500">{ev.message}</p>
            )}
          </div>
        </li>
      ))}
      {status === "running" && events.length === 0 && (
        <li className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600">
          Verbindung wird aufgebaut ...
        </li>
      )}
    </ol>
  );
}

import { TaskTypeCard } from "@/components/TaskTypeCard";
import { TASK_TYPES } from "@/lib/taskTypes";

export default function LandingPage() {
  return (
    <div className="space-y-10">
      <section className="space-y-3">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
          Pruefungsaufgaben aus Studienmaterial erzeugen
        </h1>
        <p className="max-w-3xl text-slate-600">
          Lade ein PDF hoch oder fuege Text ein und waehle den Aufgabentyp. Das
          System extrahiert Inhalte seitenweise, generiert mit einem
          LLM-Agenten Kandidatenfragen je Chunk und reduziert sie anschliessend
          auf exakt 10 finale Aufgaben inklusive Bewertungsschema bzw.
          Musterloesung. Das Ergebnis kann als Excel heruntergeladen werden.
        </p>
      </section>

      <section>
        <h2 className="mb-4 text-lg font-semibold text-slate-800">
          Aufgabentyp waehlen
        </h2>
        <div className="grid gap-5 md:grid-cols-2">
          {TASK_TYPES.map((t) => (
            <TaskTypeCard key={t.id} meta={t} />
          ))}
        </div>
      </section>
    </div>
  );
}

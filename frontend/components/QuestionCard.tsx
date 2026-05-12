"use client";

import { useState } from "react";
import type { QAPair } from "@/lib/api";

export function QuestionCard({ qa, index }: { qa: QAPair; index: number }) {
  const [open, setOpen] = useState(false);

  return (
    <article className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="flex items-start justify-between gap-3 p-4">
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span className="rounded-full bg-brand-100 px-2 py-0.5 text-brand-800">
              #{index + 1}
            </span>
            {qa.question_type && (
              <span className="rounded-full bg-slate-100 px-2 py-0.5">
                {qa.question_type}
              </span>
            )}
            {qa.klausur_subtype && (
              <span className="rounded-full bg-slate-100 px-2 py-0.5">
                {qa.klausur_subtype}
              </span>
            )}
            {qa.einsende_subtype && (
              <span className="rounded-full bg-slate-100 px-2 py-0.5">
                {qa.einsende_subtype}
              </span>
            )}
            {qa.difficulty_level && (
              <span className="rounded-full bg-slate-100 px-2 py-0.5">
                {qa.difficulty_level}
              </span>
            )}
            <span className="rounded-full bg-slate-100 px-2 py-0.5">
              {qa.academic_level}
            </span>
            <span className="rounded-full bg-slate-100 px-2 py-0.5">
              Seite {qa.source_page}
            </span>
            <span className="rounded-full bg-slate-100 px-2 py-0.5">
              {qa.core_topic}
            </span>
          </div>
          <p className="mt-2 text-base font-medium text-slate-900">
            {qa.question}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="shrink-0 rounded-xl border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:border-brand-400 hover:text-brand-700"
        >
          {open ? "Details ausblenden" : "Details anzeigen"}
        </button>
      </header>

      {open && (
        <div className="space-y-4 border-t border-slate-100 px-4 py-4 text-sm">
          <Section title="Umfang">{qa.scope}</Section>
          {qa.execution_format && (
            <Section title="Ausfuehrungsformat">{qa.execution_format}</Section>
          )}
          <Section title="Hinweise fuer Pruefende">
            {qa.guideline_examiner}
          </Section>
          <Section title="Hinweise fuer Studierende">
            <pre className="whitespace-pre-wrap font-sans">
              {qa.guideline_student}
            </pre>
          </Section>
          {qa.bewertungsschema_rubric && (
            <Section title="Bewertungsschema">
              <pre className="whitespace-pre-wrap font-sans">
                {qa.bewertungsschema_rubric}
              </pre>
            </Section>
          )}
          {qa.musterloesung_text && (
            <Section title="Musterloesung">
              <pre className="whitespace-pre-wrap font-sans">
                {qa.musterloesung_text}
              </pre>
            </Section>
          )}
          {qa.musterloesung_rubric && (
            <Section title="Bewertungsrubrik">
              <pre className="whitespace-pre-wrap font-sans">
                {qa.musterloesung_rubric}
              </pre>
            </Section>
          )}
        </div>
      )}
    </article>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </h4>
      <div className="text-slate-700">{children}</div>
    </div>
  );
}

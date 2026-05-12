import Link from "next/link";
import type { TaskTypeMeta } from "@/lib/taskTypes";

export function TaskTypeCard({ meta }: { meta: TaskTypeMeta }) {
  return (
    <Link
      href={`/new/${meta.id}`}
      className="group block rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-brand-400 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-brand-500"
    >
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-semibold text-brand-800">{meta.label}</h3>
        <span className="text-xs uppercase tracking-wide text-brand-500 group-hover:text-brand-700">
          {meta.shortLabel}
        </span>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-slate-600">
        {meta.description}
      </p>
      <p className="mt-4 text-xs text-slate-500">Default-Umfang: {meta.defaultScope}</p>
    </Link>
  );
}

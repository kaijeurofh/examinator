import { notFound } from "next/navigation";
import { NewJobForm } from "./NewJobForm";
import { getTaskMeta } from "@/lib/taskTypes";

export default function NewJobPage({
  params,
}: {
  params: { taskType: string };
}) {
  const meta = getTaskMeta(params.taskType);
  if (!meta) {
    notFound();
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <p className="text-xs uppercase tracking-wide text-brand-500">
          {meta.shortLabel}
        </p>
        <h1 className="text-2xl font-semibold text-slate-900">{meta.label}</h1>
        <p className="mt-2 text-sm text-slate-600">{meta.description}</p>
      </header>

      <NewJobForm taskType={meta.id} defaultScope={meta.defaultScope} />
    </div>
  );
}

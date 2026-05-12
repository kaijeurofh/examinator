import type { JobConfig } from "./taskTypes";

// All API calls go to the same origin as the frontend. The Next.js server
// reverse-proxies `/api/*` to the FastAPI backend (see `next.config.mjs`).
// This means the bundle does not need to know the backend's host or port,
// so the same image works on localhost, over the company VPN, behind a
// reverse proxy, etc. Setting NEXT_PUBLIC_API_URL is still supported as
// an escape hatch for setups where the backend is reached directly.
export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";

export interface CreateJobOptions {
  config: JobConfig;
  pdf?: File | null;
  text?: string | null;
}

export interface CreateJobResponse {
  job_id: string;
}

export async function createJob(opts: CreateJobOptions): Promise<CreateJobResponse> {
  const form = new FormData();
  form.append("config", JSON.stringify(opts.config));
  if (opts.pdf) {
    form.append("pdf", opts.pdf);
  }
  if (opts.text && opts.text.trim().length > 0) {
    form.append("text", opts.text);
  }

  const res = await fetch(`${API_BASE}/api/jobs`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const detail = await safeReadDetail(res);
    throw new Error(`Job konnte nicht erstellt werden (${res.status}): ${detail}`);
  }
  return (await res.json()) as CreateJobResponse;
}

export interface QAPair {
  question: string;
  question_type?: string;
  academic_level: string;
  scope: string;
  core_topic: string;
  guideline_examiner: string;
  guideline_student: string;
  source_page: number;
  bewertungsschema_rubric?: string;
  musterloesung_text?: string;
  musterloesung_rubric?: string;
  execution_format?: string;
  klausur_subtype?: string;
  einsende_subtype?: string;
  difficulty_level?: string;
}

export interface JobResult {
  questions: QAPair[];
}

export interface ProgressEventData {
  stage: string;
  message?: string;
  current?: number;
  total?: number;
}

export interface JobSnapshot {
  job_id: string;
  status: "queued" | "running" | "done" | "error";
  task_type: string;
  error?: string | null;
  events: ProgressEventData[];
  result?: JobResult;
}

export async function getJob(id: string): Promise<JobSnapshot> {
  const res = await fetch(`${API_BASE}/api/jobs/${id}`);
  if (!res.ok) {
    throw new Error(`Job ${id} nicht gefunden (${res.status})`);
  }
  return (await res.json()) as JobSnapshot;
}

export function excelDownloadUrl(id: string): string {
  return `${API_BASE}/api/jobs/${id}/excel`;
}

export function eventStreamUrl(id: string): string {
  return `${API_BASE}/api/jobs/${id}/events`;
}

async function safeReadDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return typeof body?.detail === "string"
      ? body.detail
      : JSON.stringify(body?.detail ?? body);
  } catch {
    return res.statusText;
  }
}

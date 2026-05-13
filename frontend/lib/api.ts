import type { JobConfig } from "./taskTypes";

/** Configured build-time API URL (baked into the bundle via NEXT_PUBLIC_API_URL). */
const CONFIGURED_API_BASE: string =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

/**
 * Resolve the backend URL the browser should talk to.
 *
 * The bundle is built with ``NEXT_PUBLIC_API_URL=http://127.0.0.1:${BACKEND_PORT}``
 * because that's the only origin Chrome on Windows can reach reliably when
 * the user opens the app via ``localhost``. The downside: any *other* host
 * loading the bundle (VPN client hitting ``http://192.168.x.y:3040``, a
 * teammate on the LAN, ...) would try to call its own loopback, which fails
 * with ``ERR_CONNECTION_REFUSED``.
 *
 * Fix: when the configured base is a loopback URL but the page itself wasn't
 * served from loopback, swap the host portion with the host the user actually
 * visited. The backend port mapping (``BACKEND_PORT:8000``) is exposed on the
 * same host interface, so this works without any additional reverse proxy.
 *
 * Server-side renders (no ``window``) just return the configured value
 * unchanged; only client code performs network requests.
 */
function resolveApiBase(): string {
  if (typeof window === "undefined") {
    return CONFIGURED_API_BASE;
  }
  let parsed: URL;
  try {
    parsed = new URL(CONFIGURED_API_BASE);
  } catch {
    return CONFIGURED_API_BASE;
  }
  const LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "::1", "[::1]"]);
  const baseIsLoopback = LOOPBACK_HOSTS.has(parsed.hostname);
  const pageIsLoopback = LOOPBACK_HOSTS.has(window.location.hostname);
  if (baseIsLoopback && !pageIsLoopback) {
    const port = parsed.port ? `:${parsed.port}` : "";
    return `${parsed.protocol}//${window.location.hostname}${port}`;
  }
  return CONFIGURED_API_BASE;
}

/**
 * Backend URL for the current browsing context. Re-evaluated per call so the
 * detection logic runs once ``window`` is available; the cost is negligible
 * (one URL parse) and avoids the SSR-time pitfall of capturing the wrong
 * host into a module-level constant.
 */
export function apiBase(): string {
  return resolveApiBase();
}

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

  const res = await fetch(`${apiBase()}/api/jobs`, {
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
  const res = await fetch(`${apiBase()}/api/jobs/${id}`);
  if (!res.ok) {
    throw new Error(`Job ${id} nicht gefunden (${res.status})`);
  }
  return (await res.json()) as JobSnapshot;
}

export function excelDownloadUrl(id: string): string {
  return `${apiBase()}/api/jobs/${id}/excel`;
}

export function eventStreamUrl(id: string): string {
  return `${apiBase()}/api/jobs/${id}/events`;
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

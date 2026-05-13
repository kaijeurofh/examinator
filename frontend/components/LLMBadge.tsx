import {
  IS_LOCAL_LLM,
  LLM_MODEL,
  LLM_PROVIDER,
  displayModel,
} from "@/lib/llmInfo";

/**
 * Small header chip that tells the user *which* LLM this deployment is wired
 * to. Rendered as a Server Component so the env values are read at build time
 * (in the docker image) rather than leaked into a hydration mismatch.
 *
 * The visual treatment changes with the provider:
 *   - ``ollama``  -> emerald dot + "Lokal" badge: signals on-device inference
 *                    (data stays on the host, no API key, no outbound calls).
 *   - any other   -> neutral slate "Cloud" badge for cloud APIs.
 *   - unset       -> renders nothing, so a bare ``next dev`` without compose
 *                    args doesn't show a misleading placeholder.
 */
export function LLMBadge() {
  if (!LLM_PROVIDER) {
    return null;
  }

  if (IS_LOCAL_LLM) {
    return (
      <div
        className="hidden items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800 sm:inline-flex"
        title={`Lokales LLM via Ollama: ${LLM_MODEL || "unbekannt"}`}
      >
        <span
          className="inline-block h-2 w-2 animate-pulse rounded-full bg-emerald-500"
          aria-hidden="true"
        />
        <span>Lokal</span>
        {LLM_MODEL && (
          <>
            <span className="text-emerald-300" aria-hidden="true">
              ·
            </span>
            <span className="font-mono text-[11px] tracking-tight">
              {displayModel(LLM_MODEL)}
            </span>
          </>
        )}
      </div>
    );
  }

  return (
    <div
      className="hidden items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700 sm:inline-flex"
      title={`Cloud LLM (${LLM_PROVIDER}): ${LLM_MODEL || "unbekannt"}`}
    >
      <span>Cloud</span>
      {LLM_MODEL && (
        <>
          <span className="text-slate-300" aria-hidden="true">
            ·
          </span>
          <span className="font-mono text-[11px] tracking-tight">
            {displayModel(LLM_MODEL)}
          </span>
        </>
      )}
    </div>
  );
}

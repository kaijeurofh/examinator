/**
 * Build-time LLM identity exposed to the UI as a header badge.
 *
 * The Dockerfile bakes `NEXT_PUBLIC_LLM_PROVIDER` and `NEXT_PUBLIC_LLM_MODEL`
 * into the client bundle from the same env knobs the backend reads, so the
 * badge always reflects what this deployment is *actually* configured to
 * talk to. When the values are empty (e.g. during a local `next dev` without
 * the docker-compose layer setting them), the badge hides itself instead of
 * showing a misleading placeholder.
 */

/** The provider this deployment is wired to (`ollama`, `openai`, ...). */
export const LLM_PROVIDER: string =
  process.env.NEXT_PUBLIC_LLM_PROVIDER?.trim().toLowerCase() ?? "";

/** Raw model tag, exactly as configured server-side (e.g. ``gemma4:31b``). */
export const LLM_MODEL: string = process.env.NEXT_PUBLIC_LLM_MODEL?.trim() ?? "";

/** True when this build is wired to a local Ollama daemon. */
export const IS_LOCAL_LLM = LLM_PROVIDER === "ollama";

/**
 * Shorten a model tag so it fits next to the brand wordmark without wrapping.
 *
 * HuggingFace tags like
 * ``hf.co/mradermacher/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-i1-GGUF:Q4_K_M``
 * are too long for a header chip; we keep the segment after the last ``/``
 * (which is usually the meaningful "repo:tag" portion) and ellide the rest.
 */
export function displayModel(tag: string, maxLen: number = 28): string {
  if (!tag) return "";
  const tail = tag.includes("/") ? tag.slice(tag.lastIndexOf("/") + 1) : tag;
  if (tail.length <= maxLen) return tail;
  return `${tail.slice(0, maxLen - 1)}…`;
}

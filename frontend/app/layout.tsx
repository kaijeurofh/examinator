import type { Metadata } from "next";
import Link from "next/link";
import { LLMBadge } from "@/components/LLMBadge";
import { IS_LOCAL_LLM, LLM_MODEL, displayModel } from "@/lib/llmInfo";
import "./globals.css";

// Title carries a "Lokal" suffix on the on-device build so it's immediately
// obvious in the browser tab / window switcher that this is *not* the cloud
// deployment. Plain "Examinator" otherwise.
export const metadata: Metadata = {
  title: IS_LOCAL_LLM ? "Examinator (Lokal)" : "Examinator",
  description:
    "Pruefungsaufgaben fuer Hochschulen generieren: Hausarbeit, Projekt, Klausur, Einsendeaufgabe.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="de">
      <body>
        <div className="min-h-screen flex flex-col">
          <header className="border-b border-slate-200 bg-white">
            <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between gap-4">
              <Link
                href="/"
                className="flex items-center gap-3 font-semibold text-lg text-brand-800"
              >
                <span>Examinator</span>
                {IS_LOCAL_LLM && (
                  <span className="rounded-md bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-700">
                    Lokal
                  </span>
                )}
              </Link>
              <div className="flex items-center gap-4">
                <LLMBadge />
                <nav className="hidden text-sm text-slate-600 md:block">
                  Pruefungsaufgaben aus Studienmaterial generieren
                </nav>
              </div>
            </div>
          </header>
          <main className="flex-1">
            <div className="mx-auto max-w-6xl px-6 py-10">{children}</div>
          </main>
          <footer className="border-t border-slate-200 bg-white">
            <div className="mx-auto max-w-6xl px-6 py-4 text-xs text-slate-500 flex flex-wrap items-center justify-between gap-2">
              <span>
                Hochschulinternes Tool. Stateless: keine Speicherung der
                Eingaben.
              </span>
              {IS_LOCAL_LLM && (
                <span>
                  Inferenz lokal via Ollama
                  {LLM_MODEL && (
                    <>
                      {" "}
                      ·{" "}
                      <span className="font-mono">
                        {displayModel(LLM_MODEL, 48)}
                      </span>
                    </>
                  )}
                </span>
              )}
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}

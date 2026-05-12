import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Examinator",
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
            <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between">
              <Link href="/" className="font-semibold text-lg text-brand-800">
                Examinator
              </Link>
              <nav className="text-sm text-slate-600">
                Pruefungsaufgaben aus Studienmaterial generieren
              </nav>
            </div>
          </header>
          <main className="flex-1">
            <div className="mx-auto max-w-6xl px-6 py-10">{children}</div>
          </main>
          <footer className="border-t border-slate-200 bg-white">
            <div className="mx-auto max-w-6xl px-6 py-4 text-xs text-slate-500">
              Hochschulinternes Tool. Stateless: keine Speicherung der Eingaben.
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}

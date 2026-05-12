"use client";

import { useCallback, useRef, useState } from "react";

interface DropzoneProps {
  value: File | null;
  onChange: (file: File | null) => void;
  accept?: string;
  maxMb?: number;
}

export function Dropzone({
  value,
  onChange,
  accept = "application/pdf",
  maxMb = 20,
}: DropzoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [hover, setHover] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      setError(null);
      if (!files || files.length === 0) {
        onChange(null);
        return;
      }
      const file = files[0];
      if (accept && !file.type.match(accept.replace("*", ".*"))) {
        setError(`Nur ${accept}-Dateien werden unterstuetzt.`);
        return;
      }
      if (file.size > maxMb * 1024 * 1024) {
        setError(`Datei ist groesser als ${maxMb} MB.`);
        return;
      }
      onChange(file);
    },
    [accept, maxMb, onChange]
  );

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setHover(true);
        }}
        onDragLeave={() => setHover(false)}
        onDrop={(e) => {
          e.preventDefault();
          setHover(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={`flex w-full flex-col items-center justify-center gap-1 rounded-2xl border-2 border-dashed px-6 py-10 transition ${
          hover
            ? "border-brand-500 bg-brand-50"
            : "border-slate-300 bg-white hover:border-brand-400 hover:bg-slate-50"
        }`}
      >
        <span className="text-sm font-medium text-slate-700">
          {value ? value.name : "PDF hierher ziehen oder klicken zum Auswaehlen"}
        </span>
        <span className="text-xs text-slate-500">
          {value
            ? `${(value.size / 1024 / 1024).toFixed(2)} MB`
            : `max. ${maxMb} MB`}
        </span>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </button>
      {value && (
        <button
          type="button"
          onClick={() => {
            onChange(null);
            if (inputRef.current) inputRef.current.value = "";
          }}
          className="text-xs text-slate-500 hover:text-slate-700"
        >
          Auswahl entfernen
        </button>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}

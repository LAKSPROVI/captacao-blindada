"use client";

import { useState } from "react";
import { Keyboard, X } from "lucide-react";

const SHORTCUTS = [
  { keys: "Ctrl+K", desc: "Pesquisa Pontual" },
  { keys: "Ctrl+H", desc: "Dashboard" },
  { keys: "Ctrl+1", desc: "Captação" },
  { keys: "Ctrl+2", desc: "Monitor DJEN" },
  { keys: "Ctrl+3", desc: "Processos" },
];

export function KeyboardShortcutsHelp() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="p-1.5 rounded-lg hover:bg-[var(--secondary)] text-[var(--muted-foreground)] transition-colors"
        title="Atalhos de teclado"
      >
        <Keyboard className="w-4 h-4" />
      </button>
      {open && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <div className="relative bg-[var(--card)] border rounded-xl shadow-2xl p-6 w-full max-w-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold flex items-center gap-2"><Keyboard className="w-5 h-5" /> Atalhos de Teclado</h3>
              <button onClick={() => setOpen(false)} className="p-1 hover:bg-[var(--secondary)] rounded"><X className="w-4 h-4" /></button>
            </div>
            <div className="space-y-2">
              {SHORTCUTS.map((s) => (
                <div key={s.keys} className="flex justify-between items-center py-1.5">
                  <span className="text-sm text-[var(--muted-foreground)]">{s.desc}</span>
                  <kbd className="px-2 py-1 bg-[var(--secondary)] rounded text-xs font-mono font-bold">{s.keys}</kbd>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

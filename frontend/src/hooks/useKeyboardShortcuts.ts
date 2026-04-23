"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export function useKeyboardShortcuts() {
  const router = useRouter();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Ctrl+K or Cmd+K = Focus search / go to busca
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        router.push("/busca");
      }
      // Ctrl+H = Dashboard
      if ((e.ctrlKey || e.metaKey) && e.key === "h") {
        e.preventDefault();
        router.push("/");
      }
      // Ctrl+1 = Captação
      if ((e.ctrlKey || e.metaKey) && e.key === "1") {
        e.preventDefault();
        router.push("/captacao");
      }
      // Ctrl+2 = Monitor
      if ((e.ctrlKey || e.metaKey) && e.key === "2") {
        e.preventDefault();
        router.push("/monitor");
      }
      // Ctrl+3 = Processos
      if ((e.ctrlKey || e.metaKey) && e.key === "3") {
        e.preventDefault();
        router.push("/processo");
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [router]);
}

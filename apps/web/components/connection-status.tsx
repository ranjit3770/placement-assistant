"use client";
import { useEffect, useState } from "react";

export function ConnectionStatus() {
  const [state, setState] = useState<
    "loading" | "ready" | "degraded" | "unavailable"
  >("loading");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    fetch("/ready", { signal: controller.signal, cache: "no-store" })
      .then(async (response) => {
        const result: unknown = await response.json();
        if (
          !response.ok ||
          typeof result !== "object" ||
          result === null ||
          !("status" in result) ||
          result.status !== "ready"
        )
          throw new Error("Unavailable");
        if (active)
          setState(
            "degraded" in result && result.degraded === true
              ? "degraded"
              : "ready",
          );
      })
      .catch(() => {
        if (active) setState("unavailable");
      })
      .finally(() => clearTimeout(timeout));
    return () => {
      active = false;
      clearTimeout(timeout);
      controller.abort();
    };
  }, [attempt]);
  const labels = {
    loading: "Checking connection…",
    ready: "Platform connected",
    degraded: "Platform connected · Some services unavailable",
    unavailable: "Platform connection unavailable",
  };
  return (
    <div className="connection">
      <p role="status" aria-live="polite">
        <span className={`dot ${state}`} />
        {labels[state]}
      </p>
      {state === "unavailable" && (
        <button
          onClick={() => {
            setState("loading");
            setAttempt((v) => v + 1);
          }}
        >
          Try again
        </button>
      )}
    </div>
  );
}

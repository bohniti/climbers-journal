"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "onboarding_complete";

interface TourStep {
  target: string; // data-tour-step value
  title: string;
  description: string;
}

const STEPS: TourStep[] = [
  {
    target: "",
    title: "Welcome to Climbers Journal",
    description:
      "Your unified training log for climbing and endurance. Let\u2019s take a quick look around.",
  },
  {
    target: "import",
    title: "Import your data",
    description:
      "Start by importing your climbing history from CSV or syncing endurance activities from intervals.icu.",
  },
  {
    target: "log-session",
    title: "Log a session",
    description:
      "Log climbing sessions via the form, or let the copilot do it for you from a natural-language description.",
  },
  {
    target: "copilot",
    title: "Ask the copilot",
    description:
      'Ask about your training: "What did I climb last week?" or "Show my grade progression."',
  },
  {
    target: "dashboard",
    title: "Track your progress",
    description:
      "See your weekly activity, grade pyramid, and recent sessions at a glance.",
  },
];

export default function OnboardingTour({ show, onClose }: { show: boolean; onClose: () => void }) {
  const [current, setCurrent] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);

  const step = STEPS[current];

  const measureTarget = useCallback(() => {
    if (!step.target) {
      setRect(null);
      return;
    }
    const el = document.querySelector(`[data-tour-step="${step.target}"]`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "nearest" });
      // Small delay to let scroll finish before measuring
      requestAnimationFrame(() => {
        setRect(el.getBoundingClientRect());
      });
    } else {
      setRect(null);
    }
  }, [step.target]);

  useEffect(() => {
    if (!show) return;
    measureTarget();
    window.addEventListener("resize", measureTarget);
    return () => window.removeEventListener("resize", measureTarget);
  }, [show, measureTarget]);

  const finish = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, "true");
    setCurrent(0);
    onClose();
  }, [onClose]);

  const next = useCallback(() => {
    if (current < STEPS.length - 1) {
      setCurrent((c) => c + 1);
    } else {
      finish();
    }
  }, [current, finish]);

  const prev = useCallback(() => {
    setCurrent((c) => Math.max(0, c - 1));
  }, []);

  useEffect(() => {
    if (!show) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") finish();
      if (e.key === "ArrowRight") next();
      if (e.key === "ArrowLeft") prev();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [show, finish, next, prev]);

  if (!show) return null;

  // Tooltip positioning: prefer below the target, fall back to center
  const PAD = 8;
  const tooltipStyle: React.CSSProperties = rect
    ? {
        position: "fixed",
        top: rect.bottom + PAD,
        left: Math.max(16, Math.min(rect.left, window.innerWidth - 340)),
        width: 320,
      }
    : {
        position: "fixed",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        width: 360,
      };

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-[100] bg-black/60" onClick={finish} />

      {/* Highlight cutout */}
      {rect && (
        <div
          className="fixed z-[101] rounded-lg border-2 border-emerald-500 pointer-events-none"
          style={{
            top: rect.top - PAD,
            left: rect.left - PAD,
            width: rect.width + PAD * 2,
            height: rect.height + PAD * 2,
            boxShadow: "0 0 0 9999px rgba(0,0,0,0.60)",
          }}
        />
      )}

      {/* Tooltip card */}
      <div
        className="z-[102] rounded-xl border border-slate-700 bg-slate-900 p-5 shadow-xl"
        style={tooltipStyle}
      >
        <h3 className="mb-1 text-sm font-semibold text-slate-100">
          {step.title}
        </h3>
        <p className="mb-4 text-sm leading-relaxed text-slate-400">
          {step.description}
        </p>

        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-500">
            {current + 1} / {STEPS.length}
          </span>
          <div className="flex gap-2">
            {current > 0 && (
              <button
                onClick={prev}
                className="rounded-md border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:bg-slate-800"
              >
                Back
              </button>
            )}
            <button
              onClick={finish}
              className="rounded-md border border-slate-700 px-3 py-1 text-xs text-slate-400 hover:bg-slate-800"
            >
              Skip
            </button>
            <button
              onClick={next}
              className="rounded-md bg-emerald-700 px-3 py-1 text-xs font-medium text-white hover:bg-emerald-600"
            >
              {current < STEPS.length - 1 ? "Next" : "Done"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

export function useOnboardingTour() {
  const [showTour, setShowTour] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(STORAGE_KEY) !== "true") {
      setShowTour(true);
    }
  }, []);

  const startTour = useCallback(() => {
    setShowTour(true);
  }, []);

  const closeTour = useCallback(() => {
    setShowTour(false);
  }, []);

  return { showTour, startTour, closeTour };
}

export function resetOnboarding() {
  localStorage.removeItem(STORAGE_KEY);
}

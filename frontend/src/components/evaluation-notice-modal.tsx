"use client";

import { useEffect, useRef } from "react";
import { AlertCircle, X } from "lucide-react";

type Props = {
  message: string;
  onClose: () => void;
};

export default function EvaluationNoticeModal({ message, onClose }: Props) {
  const closeButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeButton.current?.focus();
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div
      className="evaluation-modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="evaluation-notice-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="evaluation-notice-title"
        aria-describedby="evaluation-notice-message"
      >
        <button
          ref={closeButton}
          className="evaluation-modal-close"
          type="button"
          onClick={onClose}
          aria-label="Close message"
        >
          <X size={18} />
        </button>
        <span className="evaluation-modal-icon"><AlertCircle size={24} /></span>
        <p className="eyebrow">UPSC Copy Checker</p>
        <h2 id="evaluation-notice-title">Evaluation couldn’t continue</h2>
        <p id="evaluation-notice-message">{message}</p>
        <button className="submit-button evaluation-modal-action" type="button" onClick={onClose}>
          Return to your upload
        </button>
      </section>
    </div>
  );
}

"use client";

import Link from "next/link";
import { FileCheck2, RefreshCw } from "lucide-react";

type Props = {
  busy: boolean;
  error?: string;
  missingSubmission?: boolean;
  onRetry: () => void;
};

const messages = [
  "Reading your answer pages",
  "Identifying question sections",
  "Preparing your evaluation",
];

export default function EvaluationLoading({
  busy,
  error,
  missingSubmission = false,
  onRetry,
}: Props) {
  return (
    <main className="evaluation-state-page">
      <section className="evaluation-state-card" aria-live="polite">
        {error ? (
          <div className="evaluation-state-error">
            <span className="evaluation-state-icon"><FileCheck2 size={25} /></span>
            <p className="eyebrow">Evaluation paused</p>
            <h1>{missingSubmission ? "No submission is waiting" : "We couldn’t complete your evaluation"}</h1>
            <p>{error}</p>
            <div className="evaluation-state-actions">
              {!missingSubmission && (
                <button className="submit-button state-retry" onClick={onRetry} disabled={busy}>
                  <RefreshCw size={16} /> Try again
                </button>
              )}
              <Link className="state-home-link" href="/">{missingSubmission ? "Upload an answer copy" : "Return to upload"}</Link>
            </div>
          </div>
        ) : (
          <div className="evaluation-state-progress">
            <div className="evaluation-orbit" aria-hidden="true">
              <span className="orbit-ring" />
              <span className="orbit-core"><FileCheck2 size={26} /></span>
            </div>
            <p className="eyebrow">Your copy is being reviewed</p>
            <h1>Preparing your evaluation</h1>
            <p className="state-description">We’re reviewing your answer against the question and UPSC standards.</p>
            <ol className="evaluation-status-list">
              {messages.map((message, index) => (
                <li key={message} className={index === 0 ? "status-active" : ""}>
                  <span>{index + 1}</span>{message}
                </li>
              ))}
            </ol>
            <span className="loading-caption">This may take a few minutes. Please keep this page open.</span>
          </div>
        )}
      </section>
    </main>
  );
}

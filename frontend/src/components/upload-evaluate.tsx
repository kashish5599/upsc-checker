"use client";

import { useState } from "react";
import { ArrowRight, FileCheck2, LockKeyhole } from "lucide-react";
import FileDropzone, { type PdfFile } from "./file-dropzone";

function StepTitle({
  number,
  title,
  badge,
}: {
  number: string;
  title: string;
  badge: string;
}) {
  return (
    <div className="step-title">
      <span className="step-bubble">{number}</span>
      <h3>{title}</h3>
      <span className={badge === "Required" ? "badge badge-required" : "badge"}>
        {badge}
      </span>
    </div>
  );
}

export default function UploadEvaluate() {
  const [answerFiles, setAnswerFiles] = useState<PdfFile[]>([]);
  const [question, setQuestion] = useState("");
  return (
    <section className="upload-card-panel" aria-labelledby="upload-heading">
      <h2 id="upload-heading">Upload and Evaluate</h2>
      <p className="panel-subtitle">
        Your question is usually included in your answer copy, so uploading it
        separately is optional.
      </p>
      <div className="answer-section">
        <StepTitle
          number="1"
          title="Handwritten Answer Copy"
          badge="Required"
        />
        <p className="input-description">
          Upload a single PDF containing your complete answer copy.
        </p>
        <FileDropzone
          onFilesChange={setAnswerFiles}
          label="Handwritten Answer Copy PDF"
        />
      </div>
      <div className="optional-inputs">
        <section className="secondary-input">
          <StepTitle number="2" title="Reference Material" badge="Optional" />
          <p className="input-description">
            Upload any PDFs you used for your preparation (notes, reports,
            articles, etc.).
          </p>
          <FileDropzone
            multiple
            label="Reference Material PDFs"
            compact
          />
        </section>
        <section className="secondary-input question-section">
          <StepTitle number="3" title="Question Text" badge="Optional" />
          <p className="input-description">
            Not required — the question is usually included in your answer copy.
            Add it here only if you want to provide it separately.
          </p>
          <label className="visually-hidden" htmlFor="question-text">
            Question text (optional)
          </label>
          <textarea
            id="question-text"
            value={question}
            onChange={(event) => setQuestion(event.target.value.slice(0, 2000))}
            maxLength={2000}
            placeholder="Paste the question here (optional)..."
          />
          <div className="character-count" aria-live="polite">
            {question.length}/2000
          </div>
        </section>
      </div>
      <button
        className="submit-button"
        type="button"
        disabled={!answerFiles.length}
      >
        <FileCheck2 size={17} /> Check My Answer <ArrowRight size={20} />
      </button>
      <p className="privacy-note">
        <LockKeyhole size={14} /> Your files are processed securely and are not
        shared.
      </p>
    </section>
  );
}

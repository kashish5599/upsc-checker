"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import EvaluationLoading from "@/components/evaluation-loading";
import Footer from "@/components/footer";
import Navbar from "@/components/navbar";
import { EvaluationApiError, submitEvaluation } from "@/lib/evaluation-api";
import {
  clearPendingSubmission,
  getPendingSubmission,
  saveLatestEvaluation,
  setEvaluationHomeNotice,
} from "@/lib/evaluation-storage";

export default function EvaluatingPage() {
  const router = useRouter();
  const started = useRef(false);
  const inFlight = useRef(false);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [missingSubmission, setMissingSubmission] = useState(false);

  const evaluate = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    setMissingSubmission(false);
    try {
      const submission = await getPendingSubmission();
      if (!submission) {
        setMissingSubmission(true);
        setError("Start from the upload page to submit an answer copy.");
        return;
      }

      const response = await submitEvaluation(
        submission.answerCopy,
        submission.referenceFiles,
        submission.questionText,
      );
      if (response.processing_status === "no_questions_detected") {
        await clearPendingSubmission().catch(() => undefined);
        try {
          setEvaluationHomeNotice(
            "No questions were detected in the uploaded answer copy. Please upload a copy containing a question and its answer.",
          );
        } catch {
          // Continue home navigation even when session storage is unavailable.
        }
        router.replace("/");
        return;
      }
      if (!Array.isArray(response.evaluation) || response.evaluation.length === 0) {
        await clearPendingSubmission().catch(() => undefined);
        try {
          setEvaluationHomeNotice(
            "The evaluation service returned no evaluation results. Please review the uploaded answer copy and try again.",
          );
        } catch {
          // Continue home navigation even when session storage is unavailable.
        }
        router.replace("/");
        return;
      }
      await saveLatestEvaluation({ answerCopy: submission.answerCopy, response });
      await clearPendingSubmission().catch(() => undefined);
      router.replace("/results");
    } catch (cause) {
      if (cause instanceof EvaluationApiError && cause.code === "no_questions_detected") {
        await clearPendingSubmission().catch(() => undefined);
        try {
          setEvaluationHomeNotice(cause.message);
        } catch {
          // Continue home navigation even when session storage is unavailable.
        }
        router.replace("/");
        return;
      }
      setError(cause instanceof Error ? cause.message : "Something went wrong while evaluating your answer.");
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }, [router]);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void evaluate();
  }, [evaluate]);

  return (
    <>
      <Navbar />
      <EvaluationLoading
        busy={busy}
        error={error}
        missingSubmission={missingSubmission}
        onRetry={() => void evaluate()}
      />
      <Footer />
    </>
  );
}

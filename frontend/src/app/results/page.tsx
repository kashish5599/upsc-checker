"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, FileText } from "lucide-react";
import Footer from "@/components/footer";
import Navbar from "@/components/navbar";
import type { EvaluatedQuestion, SimilarTopperQuestion } from "@/lib/evaluation-api";
import OverallAnalysis from "./overall-analysis";
import QuestionEvaluationPanel, { type SimilarTopperRetryState } from "./question-evaluation-panel";
import { getPageCount, getPageRange, getQuestions, retrievalQuestionText } from "./results-utils";
import {
  getLatestEvaluation,
  setEvaluationHomeNotice,
  type StoredEvaluation,
} from "@/lib/evaluation-storage";

type ResultTab = "overall" | string;

export default function ResultsPage() {
  const router = useRouter();
  const [result, setResult] = useState<StoredEvaluation | null>(null);
  const [objectUrl, setObjectUrl] = useState("");
  const [loading, setLoading] = useState(true);
  const [pdfPage, setPdfPage] = useState(1);
  const [pdfNavigationVersion, setPdfNavigationVersion] = useState(0);
  const [activeTab, setActiveTab] = useState<ResultTab>("overall");
  const [similarTopperRetries, setSimilarTopperRetries] = useState<Record<string, SimilarTopperRetryState>>({});
  const similarTopperRetryStarted = useRef(new Set<string>());

  useEffect(() => {
    let active = true;
    void getLatestEvaluation()
      .then((stored) => {
        if (!active) return;
        if (!stored) {
          setEvaluationHomeNotice("No saved evaluation was found. Submit an answer copy to view its results.");
          router.replace("/");
          return;
        }
        if (stored.response.processing_status !== "evaluated" || stored.response.evaluation.length === 0) {
          setEvaluationHomeNotice("The evaluation service returned no evaluation results. Please review the uploaded answer copy and try again.");
          router.replace("/");
          return;
        }
        setResult(stored);
        setObjectUrl(URL.createObjectURL(stored.answerCopy));
      })
      .catch(() => {
        if (!active) return;
        setEvaluationHomeNotice("We couldn’t open the saved evaluation. Please submit your answer copy again.");
        router.replace("/");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [router]);

  useEffect(() => () => {
    if (objectUrl) URL.revokeObjectURL(objectUrl);
  }, [objectUrl]);

  const questions = useMemo(() => (result ? getQuestions(result) : []), [result]);
  const pageCount = useMemo(() => (result ? getPageCount(result, questions) : 1), [result, questions]);
  const fileName = result?.answerCopy.name ?? "Answer copy";
  const pdfSource = objectUrl
    ? `${objectUrl}#page=${pdfPage}&toolbar=1&navpanes=0&view=FitH`
    : "";
  const activeQuestion = questions.find((question) => question.question_id === activeTab);
  const visiblePageRange = activeQuestion ? getPageRange(activeQuestion.pages) : "";

  async function retrySimilarTopperQuestions(question: EvaluatedQuestion) {
    const questionId = question.question_id;
    const questionText = retrievalQuestionText(question);
    if (!questionText || similarTopperRetryStarted.current.has(questionId)) return;

    similarTopperRetryStarted.current.add(questionId);
    setSimilarTopperRetries((current) => ({
      ...current,
      [questionId]: { attempted: true, loading: true },
    }));

    try {
      const params = new URLSearchParams({ question_text: questionText });
      const response = await fetch(`/api/v1/similar-topper-questions?${params.toString()}`);
      if (!response.ok) throw new Error("Similar-question retrieval failed.");
      const payload: unknown = await response.json();
      setSimilarTopperRetries((current) => ({
        ...current,
        [questionId]: {
          attempted: true,
          loading: false,
          results: Array.isArray(payload) ? payload as SimilarTopperQuestion[] : [],
        },
      }));
    } catch {
      setSimilarTopperRetries((current) => ({
        ...current,
        [questionId]: { attempted: true, loading: false, results: [] },
      }));
    }
  }

  function handleQuestionSelection(question: EvaluatedQuestion) {
    setActiveTab(question.question_id);
    setPdfPage(Math.min(pageCount, Math.max(1, question.start_page)));
    setPdfNavigationVersion((version) => version + 1);
  }

  return (
    <>
      <Navbar />
      <main className="results-page">
        <div className="results-heading">
          <Link href="/" className="results-back"><ArrowLeft size={15} /> Back to upload</Link>
          <p className="eyebrow">UPSC Copy Checker</p>
          <h1>Your answer evaluation</h1>
          <p>Review the marked copy alongside feedback for each detected question.</p>
        </div>

        {loading || !result ? (
          <div className="results-loading" aria-label="Opening evaluation results"><span className="results-spinner" /></div>
        ) : (
          <div className="results-grid">
            <section className="results-panel pdf-panel" aria-label="Uploaded answer PDF">
              {pdfSource ? (
                <iframe key={pdfNavigationVersion} className="answer-pdf-frame" src={pdfSource} title={`PDF viewer for ${fileName}`} />
              ) : (
                <div className="pdf-unavailable"><FileText size={30} /><p>The uploaded PDF is unavailable in this browser. You can still review the evaluation.</p></div>
              )}
            </section>

            <section className="results-panel results-column" aria-label="Evaluation feedback">
              <div className="results-panel-heading detected-questions-heading">
                <h2 title={`Evaluation for ${fileName}`}>Evaluation for {fileName}</h2>
              </div>
              <div className="results-tabs" role="tablist" aria-label="Evaluation sections">
                <button
                  id="tab-overall"
                  type="button"
                  role="tab"
                  aria-selected={activeTab === "overall"}
                  aria-controls="evaluation-tab-panel"
                  className={activeTab === "overall" ? "result-tab is-active" : "result-tab"}
                  onClick={() => setActiveTab("overall")}
                >
                  Overall analysis
                </button>
                {questions.map((question) => (
                  <button
                    id={`tab-${question.question_id}`}
                    key={question.question_id}
                    type="button"
                    role="tab"
                    aria-selected={activeTab === question.question_id}
                    aria-controls="evaluation-tab-panel"
                    className={activeTab === question.question_id ? "result-tab is-active" : "result-tab"}
                    onClick={() => handleQuestionSelection(question)}
                  >
                    {question.question_id}
                  </button>
                ))}
                {visiblePageRange && <span className="results-tab-pages">{visiblePageRange}</span>}
              </div>

              {activeTab === "overall" ? (
                <div id="evaluation-tab-panel" role="tabpanel" aria-labelledby="tab-overall" className="results-tab-panel">
                  <OverallAnalysis
                    questions={questions}
                    excludedPageCount={result.response.excluded_pages.length}
                  />
                </div>
              ) : activeQuestion ? (
                <div id="evaluation-tab-panel" role="tabpanel" aria-labelledby={`tab-${activeQuestion.question_id}`} className="results-tab-panel question-tab-panel">
                  <QuestionEvaluationPanel
                    question={activeQuestion}
                    similarQuestions={similarTopperRetries[activeQuestion.question_id]?.attempted
                      ? similarTopperRetries[activeQuestion.question_id].results ?? null
                      : activeQuestion.similar_topper_questions}
                    similarRetryState={similarTopperRetries[activeQuestion.question_id]}
                    onRetrySimilarQuestions={() => void retrySimilarTopperQuestions(activeQuestion)}
                  />
                </div>
              ) : null}
            </section>
          </div>
        )}
      </main>
      <Footer />
    </>
  );
}

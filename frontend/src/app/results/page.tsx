"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle2, CircleAlert, CircleX, FileText } from "lucide-react";
import Footer from "@/components/footer";
import Navbar from "@/components/navbar";
import evaluationRubric from "@/data/evaluation-rubric.json";
import type { EvaluatedQuestion } from "@/lib/evaluation-api";
import {
  getLatestEvaluation,
  setEvaluationHomeNotice,
  type StoredEvaluation,
} from "@/lib/evaluation-storage";

type ResultTab = "overall" | string;

function getQuestions(result: StoredEvaluation): EvaluatedQuestion[] {
  return result.response.processing_status === "evaluated"
    ? result.response.evaluation
    : [];
}

function getPageCount(result: StoredEvaluation, questions: EvaluatedQuestion[]) {
  const referencedPages = [
    ...questions.flatMap((question) => question.pages),
    ...result.response.pages.excluded_pages.map((page) => page.page),
  ];
  return Math.max(1, ...referencedPages);
}

function getPageRange(pages: number[]) {
  if (!pages.length) return "Pages unavailable";
  const sorted = [...pages].sort((left, right) => left - right);
  const consecutive = sorted.every((page, index) => index === 0 || page === sorted[index - 1] + 1);
  if (sorted.length === 1) return `Page ${sorted[0]}`;
  return consecutive
    ? `Pages ${sorted[0]}–${sorted[sorted.length - 1]}`
    : `Pages ${sorted.join(", ")}`;
}

function displayQuestion(question: EvaluatedQuestion) {
  return question.printed_question_text?.trim() || question.handwritten_question_text?.trim() || "Question text was not identified.";
}

function percentageMarks(score: number) {
  return `${Math.max(0, Math.min(100, Math.round(score)))}% marks`;
}

function averageScore(questions: EvaluatedQuestion[]) {
  if (!questions.length) return 0;
  const knownWeights = questions
    .map((question) => question.maximum_marks)
    .filter((marks): marks is number => marks !== null && Number.isFinite(marks) && marks > 0);
  const fallbackWeight = knownWeights.length
    ? knownWeights.reduce((sum, marks) => sum + marks, 0) / knownWeights.length
    : 1;
  const weightedTotal = questions.reduce((sum, question) => {
    const marks = question.maximum_marks;
    const weight = marks !== null && Number.isFinite(marks) && marks > 0 ? marks : fallbackWeight;
    return sum + question.evaluation.score * weight;
  }, 0);
  const totalWeight = questions.reduce((sum, question) => {
    const marks = question.maximum_marks;
    return sum + (marks !== null && Number.isFinite(marks) && marks > 0 ? marks : fallbackWeight);
  }, 0);

  return Math.round(weightedTotal / totalWeight);
}

const demandStatus = {
  fully: {
    Icon: CheckCircle2,
    label: "Question demand fully addressed",
    className: "demand-status-fully",
  },
  partially: {
    Icon: CircleAlert,
    label: "Question demand partially addressed",
    className: "demand-status-partially",
  },
  not_addressed: {
    Icon: CircleX,
    label: "Question demand not addressed",
    className: "demand-status-not-addressed",
  },
} as const;

function QuestionEvaluationPanel({ question }: { question: EvaluatedQuestion }) {
  const evaluation = question.evaluation;
  const strengths = evaluation.overall_analysis.strengths;
  const improvements = evaluation.overall_analysis.weaknesses;
  const demand = evaluation.question_demand;
  const status = demandStatus[demand.demand_addressed];
  const DemandIcon = status.Icon;

  return (
    <div className="question-evaluation-content">
      <section className="question-evaluation-summary">
        <div>
          <h3>{displayQuestion(question)}</h3>
        </div>
        <div className="question-marks-score">
          <span>Evaluation score</span>
          <strong>{percentageMarks(evaluation.score)}</strong>
        </div>
      </section>
      <div className="question-feedback-grid">
        <details className="question-feedback-section question-feedback-accordion" open>
          <summary>Question analysis</summary>
          <div className="accordion-content">
            <h4><b>Identified demands:</b></h4>
            {demand.key_sub_parts.length ? (
              <ol>{demand.key_sub_parts.map((part, index) => <li key={`expectation-${index}`}>{part}</li>)}</ol>
            ) : <p>No specific sub-parts were identified.</p>}
            <h4><b>Your performance:</b></h4>
            <div className={`demand-status ${status.className}`}>
              <DemandIcon size={19} aria-hidden="true" />
              <strong>{status.label}</strong>
            </div>
            <p>{demand.assessment}</p>
          </div>
        </details>

        <details className="question-feedback-section question-feedback-accordion" open>
          <summary>Section-wise analysis</summary>
          <div className="accordion-content section-analysis-list">
            {evaluation.section_wise_analysis.length ? evaluation.section_wise_analysis.map((section, index) => (
              <div className="section-analysis-item" key={`${question.question_id}-section-${index}`}>
                <strong>{section.section_name}</strong>
                {section.page_anchor && <span>{section.page_anchor}</span>}
                <p>{section.analysis}</p>
              </div>
            )) : <p>No section-wise analysis was returned.</p>}
          </div>
        </details>

        <details className="question-feedback-section question-feedback-accordion">
          <summary>Overall analysis</summary>
          <div className="accordion-content">
            <h4>Strengths</h4>
            {strengths.length ? <ol>{strengths.map((item, index) => <li key={`strength-${index}`}>{item}</li>)}</ol> : <p>No strengths were returned.</p>}
            <h4>Weaknesses</h4>
            {improvements.length ? <ol>{improvements.map((item, index) => <li key={`weakness-${index}`}>{item}</li>)}</ol> : <p>No weaknesses were returned.</p>}
            <h4>Assessment</h4>
            <p>{evaluation.overall_analysis.assessment}</p>
          </div>
        </details>

        <details className="question-feedback-section question-feedback-accordion">
          <summary>Suggestions</summary>
          <div className="accordion-content">
            {evaluation.suggestions_to_improve.length ? (
              <ol>{evaluation.suggestions_to_improve.map((item, index) => <li key={`suggestion-${index}`}>{item}</li>)}</ol>
            ) : <p>No suggestions were returned.</p>}
          </div>
        </details>
      </div>
    </div>
  );
}

function OverallAnalysis({
  questions,
  excludedPageCount,
}: {
  questions: EvaluatedQuestion[];
  excludedPageCount: number;
}) {
  const score = averageScore(questions);

  return (
    <div className="overall-analysis-content">
      <div className="overall-score-cards">
        <section className="overall-score-card">
          <span>Average score</span>
          <strong>{percentageMarks(score)}</strong>
          <div className="score-meter" aria-label={`Average score ${score} percent marks`}>
            <span style={{ width: `${score}%` }} />
          </div>
        </section>
        <section className="file-detection-summary-card">
          <h3>File detection summary</h3>
          <div className="detection-summary-stats">
            <div className="detection-summary-stat is-evaluated">
              <strong>{questions.length}</strong>
              <span>questions detected and evaluated</span>
            </div>
            {excludedPageCount > 0 && (
              <div className="detection-summary-stat is-excluded">
                <strong>{excludedPageCount}</strong>
                <span>pages excluded as irrelevant</span>
              </div>
            )}
          </div>
        </section>
      </div>

      <section className="overall-assessment-card">
        <h3>Overall analysis</h3>
        <div className="overall-assessments">
          {questions.map((question) => (
            <div className="overall-question-assessment" key={question.question_id}>
              <span className="overall-question-id">{question.question_id}</span>
              <p>{question.evaluation.overall_analysis.assessment}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="evaluation-rubric-card">
        <h3>Evaluation rubric</h3>
        <p className="evaluation-rubric-intro">Each answer is evaluated across the following 9 parameters (total 100 points).</p>
        <ol className="evaluation-rubric-list">
          {evaluationRubric.map((item) => (
            <li className="evaluation-rubric-item" key={item.name}>
              <span className="rubric-number">{item.number}</span>
              <strong>{item.name}</strong>
              <span className="rubric-description">{item.description}</span>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

export default function ResultsPage() {
  const router = useRouter();
  const [result, setResult] = useState<StoredEvaluation | null>(null);
  const [objectUrl, setObjectUrl] = useState("");
  const [loading, setLoading] = useState(true);
  const [pdfPage, setPdfPage] = useState(1);
  const [pdfNavigationVersion, setPdfNavigationVersion] = useState(0);
  const [activeTab, setActiveTab] = useState<ResultTab>("overall");

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
                    excludedPageCount={result.response.pages.excluded_pages.length}
                  />
                </div>
              ) : activeQuestion ? (
                <div id="evaluation-tab-panel" role="tabpanel" aria-labelledby={`tab-${activeQuestion.question_id}`} className="results-tab-panel question-tab-panel">
                  <QuestionEvaluationPanel question={activeQuestion} />
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

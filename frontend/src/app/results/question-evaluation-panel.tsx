import { CheckCircle2, CircleAlert, CircleX } from "lucide-react";
import type { EvaluatedQuestion, SimilarTopperQuestion } from "@/lib/evaluation-api";
import MarkedText from "./marked-text";
import { displayQuestion, percentageMarks, retrievalQuestionText } from "./results-utils";

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

const MIN_SIMILAR_TOPPER_QUESTION_SCORE = 0.85;

export interface SimilarTopperRetryState {
  attempted: boolean;
  loading: boolean;
  results?: SimilarTopperQuestion[];
}

export default function QuestionEvaluationPanel({
  question,
  similarQuestions,
  similarRetryState,
  onRetrySimilarQuestions,
}: {
  question: EvaluatedQuestion;
  similarQuestions: SimilarTopperQuestion[] | null;
  similarRetryState?: SimilarTopperRetryState;
  onRetrySimilarQuestions: () => void;
}) {
  const evaluation = question.evaluation;
  const strengths = evaluation.overall_analysis.strengths;
  const improvements = evaluation.overall_analysis.weaknesses;
  const demand = evaluation.question_demand;
  const status = demandStatus[demand.demand_addressed];
  const DemandIcon = status.Icon;
  const displaySimilarQuestions = similarQuestions?.filter(
    (item) => item.score >= MIN_SIMILAR_TOPPER_QUESTION_SCORE,
  ) ?? similarQuestions;

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
            {demand.key_sub_parts.length > 0 && (
              <>
                <h4><b>Identified demands:</b></h4>
                <ol>{demand.key_sub_parts.map((part, index) => <li key={`expectation-${index}`}><MarkedText text={part} /></li>)}</ol>
              </>
            )}
            <h4><b>Your performance:</b></h4>
            <div className={`demand-status ${status.className}`}>
              <DemandIcon size={19} aria-hidden="true" />
              <strong>{status.label}</strong>
            </div>
            <p><MarkedText text={demand.assessment} /></p>
          </div>
        </details>

        <details className="question-feedback-section question-feedback-accordion" open>
          <summary>Section-wise analysis</summary>
          <div className="accordion-content section-analysis-list">
            {evaluation.section_wise_analysis.length ? evaluation.section_wise_analysis.map((section, index) => (
              <div className="section-analysis-item" key={`${question.question_id}-section-${index}`}>
                <strong className="section-analysis-title">{section.section_name}</strong>
                {section.page_anchor && <span>{section.page_anchor}</span>}
                <p><MarkedText text={section.analysis} /></p>
              </div>
            )) : <p>No section-wise analysis was returned.</p>}
          </div>
        </details>

        <details className="question-feedback-section question-feedback-accordion">
          <summary>Overall analysis</summary>
          <div className="accordion-content">
            {strengths.length > 0 && (
              <>
                <h4>Strengths</h4>
                <ol>{strengths.map((item, index) => <li key={`strength-${index}`}><MarkedText text={item} /></li>)}</ol>
              </>
            )}
            {improvements.length > 0 && (
              <>
                <h4>Weaknesses</h4>
                <ol>{improvements.map((item, index) => <li key={`weakness-${index}`}><MarkedText text={item} /></li>)}</ol>
              </>
            )}
            <h4>Assessment</h4>
            <p><MarkedText text={evaluation.overall_analysis.assessment} /></p>
          </div>
        </details>

        {evaluation.suggestions_to_improve.length > 0 && (
          <details className="question-feedback-section question-feedback-accordion">
            <summary>Suggestions</summary>
            <div className="accordion-content">
              <ol>{evaluation.suggestions_to_improve.map((item, index) => <li key={`suggestion-${index}`}><MarkedText text={item} /></li>)}</ol>
            </div>
          </details>
        )}

        <details className="question-feedback-section question-feedback-accordion">
          <summary>Similar Topper Questions</summary>
          <div className="accordion-content">
            {displaySimilarQuestions === null && !similarRetryState?.attempted ? (
              <div className="similar-topper-retrieval-error">
                <p>Similar topper questions could not be retrieved.</p>
                <button
                  className="similar-topper-retry"
                  type="button"
                  onClick={onRetrySimilarQuestions}
                  disabled={!retrievalQuestionText(question)}
                >
                  Retry
                </button>
              </div>
            ) : similarRetryState?.loading ? (
              <p>Retrieving similar topper questions…</p>
            ) : displaySimilarQuestions?.length ? (
              <ol className="similar-topper-question-list">
                {displaySimilarQuestions.map((item, index) => (
                  <li key={`${question.question_id}-similar-${index}`}>
                    <p>{item.question_text}</p>
                    <div className="similar-topper-question-meta">
                      <span>{item.topper || "Topper not specified"}</span>
                      {item.question_url && (
                        <a href={item.question_url} target="_blank" rel="noopener noreferrer">
                          View question
                        </a>
                      )}
                      <span>Relevance: {Math.round(item.score * 100)}%</span>
                    </div>
                  </li>
                ))}
              </ol>
            ) : (
              <p>No similar topper questions found.</p>
            )}
          </div>
        </details>
      </div>
    </div>
  );
}

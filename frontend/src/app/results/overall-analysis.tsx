import evaluationRubric from "@/data/evaluation-rubric.json";
import type { EvaluatedQuestion } from "@/lib/evaluation-api";
import MarkedText from "./marked-text";
import { averageScore, percentageMarks } from "./results-utils";

export default function OverallAnalysis({
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
              <p><MarkedText text={question.evaluation.overall_analysis.assessment} /></p>
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

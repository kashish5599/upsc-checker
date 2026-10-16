import type { EvaluatedQuestion } from "@/lib/evaluation-api";
import type { StoredEvaluation } from "@/lib/evaluation-storage";

export function getQuestions(result: StoredEvaluation): EvaluatedQuestion[] {
  return result.response.processing_status === "evaluated"
    ? result.response.evaluation
    : [];
}

export function getPageCount(result: StoredEvaluation, questions: EvaluatedQuestion[]) {
  const referencedPages = [
    ...questions.flatMap((question) => question.pages),
    ...result.response.excluded_pages.map((page) => page.page),
  ];
  return Math.max(1, ...referencedPages);
}

export function getPageRange(pages: number[]) {
  if (!pages.length) return "Pages unavailable";
  const sorted = [...pages].sort((left, right) => left - right);
  const consecutive = sorted.every((page, index) => index === 0 || page === sorted[index - 1] + 1);
  if (sorted.length === 1) return `Page ${sorted[0]}`;
  return consecutive
    ? `Pages ${sorted[0]}–${sorted[sorted.length - 1]}`
    : `Pages ${sorted.join(", ")}`;
}

export function displayQuestion(question: EvaluatedQuestion) {
  return question.printed_question_text?.trim() || question.handwritten_question_text?.trim() || "Question text was not identified.";
}

export function retrievalQuestionText(question: EvaluatedQuestion) {
  return question.retrieval_query?.trim()
    || question.printed_question_text?.trim()
    || question.handwritten_question_text?.trim()
    || "";
}

export function percentageMarks(score: number) {
  return `${Math.max(0, Math.min(100, Math.round(score)))}% marks`;
}

export function averageScore(questions: EvaluatedQuestion[]) {
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

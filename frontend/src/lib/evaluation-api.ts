export interface RetrievedContext {
  document_id: string;
  text: string;
  score: number;
  page_start?: number | null;
  page_end?: number | null;
  chapter?: string | null;
  section?: string | null;
  [metadata: string]: unknown;
}

export interface SegmentedQuestion {
  question_id: string;
  printed_question_text: string | null;
  handwritten_question_text: string | null;
  maximum_marks: number | null;
  retrieval_query: string | null;
  start_page: number;
  pages: number[];
  context: RetrievedContext[];
}

export type ExcludedPageReason =
  | "blank"
  | "instruction"
  | "unrelated"
  | "no_answer_content";

export interface ExcludedPage {
  page: number;
  reason: ExcludedPageReason;
}

export interface AnswerSegmentation {
  questions: SegmentedQuestion[];
  excluded_pages: ExcludedPage[];
}

export interface QuestionDemand {
  directive: string | null;
  core_demand: string | null;
  key_sub_parts: string[];
  demand_addressed: "fully" | "partially" | "not_addressed";
  assessment: string;
}

export interface SectionAnalysis {
  section_name: string;
  page_anchor: string | null;
  analysis: string;
}

export interface OverallAnalysis {
  strengths: string[];
  weaknesses: string[];
  assessment: string;
}

export interface RubricScores {
  understanding_and_demand: number;
  coverage_and_relevance: number;
  depth_and_conceptual_clarity: number;
  analysis_and_reasoned_judgement: number;
  content_quality_and_accuracy: number;
  content_adequacy_and_relevant_dimensions: number;
  contextual_competence_and_value_addition: number;
  structure_coherence_and_succinctness: number;
  presentation_and_visual_communication: number;
}

export interface EvaluationDetails {
  question_demand: QuestionDemand;
  section_wise_analysis: SectionAnalysis[];
  overall_analysis: OverallAnalysis;
  rubric_scores: RubricScores;
  suggestions_to_improve: string[];
  score: number;
}

export interface EvaluatedQuestion extends SegmentedQuestion {
  evaluation: EvaluationDetails;
}

interface EvaluationResponseBase {
  pages: AnswerSegmentation;
  reference_files: string;
}

export interface EvaluatedResponse extends EvaluationResponseBase {
  processing_status: "evaluated";
  evaluation: EvaluatedQuestion[];
}

export interface NoQuestionsDetectedResponse extends EvaluationResponseBase {
  processing_status: "no_questions_detected";
}

export type EvaluationResponse =
  | EvaluatedResponse
  | NoQuestionsDetectedResponse;

export interface ValidationIssue {
  loc: Array<string | number>;
  msg: string;
  type: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
}

export interface EvaluationErrorResponse {
  detail: string | ValidationIssue[];
}

export class EvaluationApiError extends Error {
  readonly code?: string;

  constructor(message: string, code?: string) {
    super(message);
    this.name = "EvaluationApiError";
    this.code = code;
  }
}

function errorCode(payload: unknown): string | undefined {
  if (!payload || typeof payload !== "object") return undefined;
  const body = payload as { code?: unknown; detail?: unknown };
  if (typeof body.code === "string") return body.code;
  const detailText = typeof body.detail === "string"
    ? body.detail
    : Array.isArray(body.detail)
      ? body.detail.map((issue) => (issue as { msg?: unknown })?.msg).filter((message): message is string => typeof message === "string").join(" ")
      : "";
  if (/no[_\s-]*questions[_\s-]*detected|no questions (?:were )?detected/i.test(detailText)) {
    return "no_questions_detected";
  }
  return undefined;
}

function errorMessage(payload: unknown): string {
  if (!payload || typeof payload !== "object" || !("detail" in payload)) {
    return "Your answer could not be evaluated. Please try again.";
  }
  const { detail } = payload as EvaluationErrorResponse;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((issue) => issue.msg).join(" ");
  return "Your answer could not be evaluated. Please try again.";
}

export async function submitEvaluation(
  answerCopy: File,
  referenceFiles: File[],
  questionText: string,
): Promise<EvaluationResponse> {
  const form = new FormData();
  form.append("answer_copy", answerCopy, answerCopy.name);
  for (const reference of referenceFiles) {
    form.append("reference_files", reference, reference.name);
  }
  if (questionText.trim()) form.append("question_text", questionText.trim());

  let response: Response;
  try {
    response = await fetch("/api/v1/evaluate", { method: "POST", body: form });
  } catch {
    throw new EvaluationApiError(
      "We couldn’t reach the evaluation service. Check that the backend is running, then try again.",
    );
  }

  const payload: unknown = await response.json().catch(() => null);
  console.log("UPSC evaluation API response:", payload);

  if (!response.ok) {
    throw new EvaluationApiError(errorMessage(payload), errorCode(payload));
  }
  if (!payload || typeof payload !== "object") {
    throw new EvaluationApiError(
      "The evaluation service returned an unreadable response. Please try again.",
    );
  }
  return payload as EvaluationResponse;
}

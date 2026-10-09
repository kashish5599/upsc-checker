from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class QuestionDemand(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    directive: str | None = Field(description="The command word or directive in the question.")
    core_demand: str | None = Field(description="The central task the question asks the student to perform.")
    key_sub_parts: list[str] = Field(description="Distinct sub-parts and important qualifiers in the question.")
    demand_addressed: Literal["fully", "partially", "not_addressed"]
    assessment: str = Field(description="Concise assessment of how well the answer meets the demand.")


class SectionAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    section_name: str = Field(description="A concise label for the specific answer section being discussed.")
    page_anchor: str | None = Field(
        description="Specific page and visible heading, paragraph, bullet, or diagram reference; null if uncertain."
    )
    analysis: str = Field(description="Concise, actionable analysis of this part of the handwritten answer.")


class OverallAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    strengths: list[str]
    weaknesses: list[str]
    assessment: str


class RubricScores(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    understanding_and_demand: int = Field(ge=0, le=15, description="Understanding & Demand, maximum 15.")
    coverage_and_relevance: int = Field(ge=0, le=10, description="Coverage & Relevance, maximum 10.")
    depth_and_conceptual_clarity: int = Field(ge=0, le=15, description="Depth & Conceptual Clarity, maximum 15.")
    analysis_and_reasoned_judgement: int = Field(ge=0, le=15, description="Analysis & Reasoned Judgement, maximum 15.")
    content_quality_and_accuracy: int = Field(ge=0, le=10, description="Content Quality & Accuracy, maximum 10.")
    content_adequacy_and_relevant_dimensions: int = Field(
        ge=0, le=10, description="Content Adequacy & Relevant Dimensions, maximum 10."
    )
    contextual_competence_and_value_addition: int = Field(
        ge=0, le=10, description="Contextual Competence & Value Addition, maximum 10."
    )
    structure_coherence_and_succinctness: int = Field(
        ge=0, le=10, description="Structure, Coherence & Succinctness, maximum 10."
    )
    presentation_and_visual_communication: int = Field(
        ge=0, le=5, description="Presentation & Visual Communication, maximum 5."
    )

    def earned_total(self) -> int:
        return sum(self.model_dump().values())


class EvaluationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    question_demand: QuestionDemand
    section_wise_analysis: list[SectionAnalysis]
    overall_analysis: OverallAnalysis
    rubric_scores: RubricScores
    suggestions_to_improve: list[str]
    score: int = Field(
        default=0,
        ge=0,
        le=50,
        description="Calculated by the application on a 0–50 scale as half the raw rubric total, rounded down.",
    )

    @model_validator(mode="before")
    @classmethod
    def ignore_model_supplied_total(cls, value: Any) -> Any:
        if isinstance(value, dict) and "score" in value:
            return {**value, "score": 0}
        return value

    @model_validator(mode="after")
    def calculate_score(self) -> EvaluationOutput:
        self.score = min(50, self.rubric_scores.earned_total() // 2)
        return self

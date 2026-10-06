from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class EvaluationConfigurationError(RuntimeError):
    """Raised when required evaluation configuration is missing."""


@dataclass(frozen=True)
class EvaluationSettings:
    tavily_api_key: str
    model_name: str
#What about pinecone?
    @classmethod
    def from_environment(cls) -> EvaluationSettings:
        load_dotenv()
        tavily_api_key = os.getenv("TAVILY_API_KEY", "").strip()
        if not tavily_api_key:
            raise EvaluationConfigurationError("Missing required configuration: TAVILY_API_KEY.")
        return cls(
            tavily_api_key=tavily_api_key,
            model_name=os.getenv("GEMINI_EVALUATION_MODEL", "gemini-3.5-flash-lite").strip(),
        )

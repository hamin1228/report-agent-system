"""LLM-based quality gates used by generation agents."""

import json

from pydantic import BaseModel, Field

from report_agent.llm import LLMClient


class Evaluation(BaseModel):
    passed: bool
    score: int = Field(ge=0, le=100)
    feedback: str = ""


class Evaluator:
    def __init__(self, client: LLMClient, rubric: str, threshold: int = 75) -> None:
        self.client = client
        self.rubric = rubric
        self.threshold = threshold

    async def evaluate(self, payload: object) -> Evaluation:
        result = await self.client.structured(
            Evaluation,
            system="You are a strict but practical quality evaluator.",
            user=(
                f"Rubric:\n{self.rubric}\n\n"
                f"Pass only when score is at least {self.threshold}.\n"
                f"Artifact:\n{json.dumps(payload, ensure_ascii=False, default=str)}"
            ),
        )
        result.passed = result.score >= self.threshold
        return result


OUTLINE_RUBRIC = """Check topic relevance, logical section order, coverage, non-overlap,
and whether every section has concrete research questions."""
RESEARCH_RUBRIC = """Check coverage of research questions, factual specificity, source
quality, and whether claims can be traced to supplied URLs."""
SECTION_RUBRIC = """Check coverage, clarity, evidence use, citation accuracy, and whether
the section stays within its assigned scope."""
REPORT_RUBRIC = """Check global coherence, useful executive summary, consistent tone,
minimal repetition, complete references, and alignment with the original request."""

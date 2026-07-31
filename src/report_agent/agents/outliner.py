"""Outline generation agent."""

from report_agent.config import Settings
from report_agent.evaluators import OUTLINE_RUBRIC, Evaluator
from report_agent.llm import LLMClient
from report_agent.models import Outline


class OutlinerAgent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = LLMClient(settings)
        self.evaluator = Evaluator(LLMClient(settings, evaluator=True), OUTLINE_RUBRIC)

    async def run(self, request: str, requirements: str = "") -> Outline:
        feedback = ""
        last: Outline | None = None
        for _ in range(self.settings.max_evaluation_retries + 1):
            last = await self.client.structured(
                Outline,
                system=(
                    "You are a report outliner. Create a focused, non-overlapping outline "
                    "with 3-7 sections and concrete research questions."
                ),
                user=(
                    f"Request: {request}\nRequirements: {requirements or 'None'}\n"
                    f"Evaluator feedback: {feedback or 'None'}"
                ),
            )
            evaluation = await self.evaluator.evaluate(last.model_dump())
            if evaluation.passed:
                return last
            feedback = evaluation.feedback
        if last is None:
            raise RuntimeError("Outline generation produced no result")
        return last

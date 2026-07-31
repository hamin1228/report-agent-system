"""Top-level report workflow orchestration."""

from collections.abc import Awaitable, Callable

from report_agent.agents import OutlinerAgent, ResearcherWorkflow, WriterAgent
from report_agent.config import Settings
from report_agent.models import FinalReport, Outline, WorkflowPhase, WorkflowState
from report_agent.storage import ArtifactStore

ApprovalHandler = Callable[[Outline], Awaitable[tuple[bool, str]]]
ProgressHandler = Callable[[WorkflowPhase, str], None]


class OutlineRejectedError(RuntimeError):
    """Raised when a caller rejects the generated outline."""


class ReportOrchestrator:
    """Coordinates all specialized agents and persists phase outputs."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.outliner = OutlinerAgent(self.settings)
        self.researcher = ResearcherWorkflow(self.settings)
        self.writer = WriterAgent(self.settings)
        self.state: WorkflowState | None = None
        self.store: ArtifactStore | None = None

    async def run(
        self,
        request: str,
        *,
        requirements: str = "",
        approval_handler: ApprovalHandler | None = None,
        progress_handler: ProgressHandler | None = None,
    ) -> FinalReport:
        self.state = WorkflowState(request=request, requirements=requirements)
        self.store = ArtifactStore(self.settings.workspace)
        try:
            self.state.phase = WorkflowPhase.OUTLINE
            self._notify(progress_handler, "Generating and evaluating the outline")
            outline = await self.outliner.run(request, requirements)
            self.state.outline = outline
            self.store.save_outline(outline)
            self.store.save_state(self.state)

            self.state.phase = WorkflowPhase.APPROVAL
            self._notify(progress_handler, "Outline ready for approval")
            if approval_handler:
                approved, feedback = await approval_handler(outline)
                if not approved:
                    if not feedback.strip():
                        raise OutlineRejectedError("Outline rejected without revision feedback")
                    outline = await self.outliner.run(
                        request,
                        f"{requirements}\nRevision feedback: {feedback}".strip(),
                    )
                    self.state.outline = outline
                    self.store.save_outline(outline)
                    self.store.save_state(self.state)
                    approved, feedback = await approval_handler(outline)
                    if not approved:
                        raise OutlineRejectedError(feedback or "Revised outline rejected")

            self.state.phase = WorkflowPhase.RESEARCH
            self._notify(progress_handler, "Researching outline sections in parallel")
            self.state.research = await self.researcher.run(outline)
            self.store.save_research(self.state.research)
            self.store.save_state(self.state)

            self.state.phase = WorkflowPhase.WRITING
            self._notify(progress_handler, "Writing and evaluating report sections")
            self.state.report = await self.writer.run(outline, self.state.research)
            self.store.save_report(self.state.report)
            self.store.save_state(self.state)

            self.state.phase = WorkflowPhase.COMPLETE
            self.store.save_state(self.state)
            self._notify(progress_handler, "Report completed")
            return self.state.report
        except Exception as exc:
            self.state.phase = WorkflowPhase.FAILED
            self.state.errors.append(str(exc))
            if self.store:
                self.store.save_state(self.state)
            self._notify(progress_handler, f"Workflow failed: {exc}")
            raise

    def _notify(self, handler: ProgressHandler | None, message: str) -> None:
        if handler and self.state:
            handler(self.state.phase, message)

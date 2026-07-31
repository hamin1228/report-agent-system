from report_agent.agents.researcher import ResearcherWorkflow
from report_agent.config import Settings


def test_parallelism_setting_is_bounded() -> None:
    settings = Settings(max_parallel_searches=3)
    workflow = ResearcherWorkflow(settings)
    assert workflow.settings.max_parallel_searches == 3

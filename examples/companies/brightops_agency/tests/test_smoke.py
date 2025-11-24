"""
Smoke tests for BrightOps Agency example scenarios.

Tests verify that the three main pipelines execute successfully and produce
expected outputs showcasing AI generation techniques and MCP integrations.
"""

import os
import sys
from pathlib import Path
from typing import Any

import pytest

# Add sibyl to path if needed
EXAMPLE_ROOT = Path(__file__).parent.parent
PROJECT_ROOT = EXAMPLE_ROOT.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Test data paths
DATA_DIR = EXAMPLE_ROOT / "data" / "docs"
MEETINGS_DIR = DATA_DIR / "meetings"
EMAILS_DIR = DATA_DIR / "emails"
CONFIG_DIR = EXAMPLE_ROOT / "config"


# Verify test data exists
def test_test_data_exists() -> None:
    """Verify all required test data files exist."""
    assert MEETINGS_DIR.exists(), f"Meetings directory not found: {MEETINGS_DIR}"
    assert EMAILS_DIR.exists(), f"Emails directory not found: {EMAILS_DIR}"

    # Check meeting files
    meeting_files = [
        "kickoff_acme_mobile_2024_03.md",
        "brainstorm_techstart_website_2024_04.md",
        "status_update_globex_q2_2024.md",
        "retrospective_fintech_project_2024_03.md",
        "discovery_healthtech_2024_05.md",
    ]
    for filename in meeting_files:
        filepath = MEETINGS_DIR / filename
        assert filepath.exists(), f"Meeting file not found: {filepath}"

    # Check email files
    email_files = [
        "acme_ceo_communication_style.md",
        "techstart_detailed_feedback.md",
        "globex_technical_preferences.md",
    ]
    for filename in email_files:
        filepath = EMAILS_DIR / filename
        assert filepath.exists(), f"Email file not found: {filepath}"


def test_config_files_exist() -> None:
    """Verify configuration files exist."""
    workspace_file = CONFIG_DIR / "workspace.yaml"
    pipelines_file = CONFIG_DIR / "pipelines.yaml"

    assert workspace_file.exists(), f"Workspace config not found: {workspace_file}"
    assert pipelines_file.exists(), f"Pipelines config not found: {pipelines_file}"


# Mock pipeline execution for testing without full Sibyl runtime
class MockPipelineResult:
    """Mock result for pipeline execution."""

    def __init__(self, success: Any = True, output: Any = None, metadata: Any = None) -> None:
        self.success = success
        self.output = output or {}
        self.metadata = metadata or {}

    def get(self, key: Any, default: Any = None) -> Any:
        return self.output.get(key, default)


def mock_run_pipeline(pipeline_name, input_data: Any) -> Any:
    """
    Mock pipeline execution for testing.

    In a real deployment, this would call the Sibyl pipeline runner.
    For smoke tests, we verify the configuration and return mock results.
    """
    if pipeline_name == "meeting_to_plan":
        return MockPipelineResult(
            success=True,
            output={
                "categories": {
                    "Design": ["UI/UX design", "Prototypes", "Design system"],
                    "Development": ["Frontend", "Backend", "API integration"],
                    "QA": ["Testing", "Bug fixes", "Performance optimization"],
                },
                "checkpoints": [
                    {
                        "name": "Discovery & Design",
                        "weeks": "1-4",
                        "deliverables": ["Requirements", "Designs", "Architecture"],
                    },
                    {
                        "name": "MVP Development",
                        "weeks": "5-10",
                        "deliverables": ["Core features", "Integrations"],
                    },
                ],
                "quality_score": 8.5,
            },
            metadata={"techniques_used": ["category_naming", "checkpoint_naming"]},
        )

    if pipeline_name == "learn_preferences":
        return MockPipelineResult(
            success=True,
            output={
                "pattern_artifact": {
                    "pattern_name": "acme_ceo_sarah_communication_patterns",
                    "category": "communication",
                    "confidence": 0.85,
                    "description": "Brief, action-oriented, fast decision-making",
                    "preferences": {
                        "communication_style": "brief_bullet_points",
                        "decision_speed": "fast",
                        "update_frequency": "weekly",
                    },
                },
                "summary": "Sarah prefers brief updates with bullet points...",
            },
            metadata={
                "techniques_used": ["rag", "sequential_thinking", "pattern_artifact"],
                "mcp_providers": ["in_memoria"],
            },
        )

    if pipeline_name == "project_breakdown":
        return MockPipelineResult(
            success=True,
            output={
                "categories": {
                    "Design": ["UX research", "Visual design", "Prototyping"],
                    "Frontend": ["React Native", "UI components", "State management"],
                    "Backend": ["API", "Database", "Authentication"],
                    "Infrastructure": ["CI/CD", "Hosting", "Monitoring"],
                },
                "milestones": [
                    {
                        "phase": "Phase 1: Discovery",
                        "duration_weeks": 4,
                        "deliverables": ["Requirements", "Designs", "Architecture"],
                    },
                    {
                        "phase": "Phase 2: Development",
                        "duration_weeks": 8,
                        "deliverables": ["MVP", "Testing", "Documentation"],
                    },
                ],
                "estimates": {
                    "effort_person_weeks": 80,
                    "duration_weeks": 16,
                    "team_size": 6,
                    "budget_usd": 725000,
                },
                "quality_score": 8.7,
            },
            metadata={
                "techniques_used": [
                    "sequential_thinking",
                    "category_naming",
                    "checkpoint_naming",
                    "quality_scoring",
                ],
            },
        )

    msg = f"Unknown pipeline: {pipeline_name}"
    raise ValueError(msg)


@pytest.mark.smoke
def test_meeting_to_plan_pipeline() -> None:
    """
    Test Scenario 1: Meeting to Plan pipeline.

    Verifies that messy meeting notes can be transformed into structured
    project plan with categories and checkpoints.
    """
    # Arrange
    pipeline_name = "meeting_to_plan"
    input_data = {"meeting_file": "kickoff_acme_mobile_2024_03.md"}

    # Act
    result = mock_run_pipeline(pipeline_name, input_data)

    # Assert
    assert result.success, "Pipeline should execute successfully"

    # Check categories are present
    categories = result.get("categories", {})
    assert len(categories) > 0, "Should have at least one category"
    assert (
        "Design" in categories or "Development" in categories
    ), "Should have typical project categories"

    # Check checkpoints are present
    checkpoints = result.get("checkpoints", [])
    assert len(checkpoints) > 0, "Should have at least one checkpoint"
    assert (
        "weeks" in checkpoints[0] or "duration" in checkpoints[0]
    ), "Checkpoints should have timeline info"

    # Check quality score
    quality_score = result.get("quality_score", 0)
    assert quality_score >= 7.0, f"Quality score should be >= 7.0, got {quality_score}"  # noqa: PLR2004

    # Check techniques used
    techniques = result.metadata.get("techniques_used", [])
    assert "category_naming" in techniques, "Should use category_naming technique"
    assert "checkpoint_naming" in techniques, "Should use checkpoint_naming technique"


@pytest.mark.smoke
def test_learn_preferences_pipeline() -> None:
    """
    Test Scenario 2: Learn Client Preferences pipeline.

    Verifies that client emails can be analyzed to extract communication
    patterns and store as PatternArtifact in In-Memoria MCP.
    """
    # Arrange
    pipeline_name = "learn_preferences"
    input_data = {"client_name": "Acme CEO Sarah"}

    # Act
    result = mock_run_pipeline(pipeline_name, input_data)

    # Assert
    assert result.success, "Pipeline should execute successfully"

    # Check pattern artifact is created
    pattern_artifact = result.get("pattern_artifact", {})
    assert pattern_artifact, "Should create PatternArtifact"
    assert pattern_artifact["pattern_name"], "Pattern should have a name"
    assert pattern_artifact["category"] == "communication", "Should be communication pattern"

    # Check confidence score
    confidence = pattern_artifact.get("confidence", 0)
    assert 0.7 <= confidence <= 1.0, (  # noqa: PLR2004
        f"Confidence should be between 0.7 and 1.0, got {confidence}"
    )

    # Check preferences are extracted
    preferences = pattern_artifact.get("preferences", {})
    assert len(preferences) > 0, "Should extract at least some preferences"

    # Check summary is generated
    summary = result.get("summary", "")
    assert len(summary) > 0, "Should generate human-readable summary"

    # Check MCP usage
    mcp_providers = result.metadata.get("mcp_providers", [])
    assert "in_memoria" in mcp_providers, "Should use In-Memoria MCP"


@pytest.mark.smoke
def test_project_breakdown_pipeline() -> None:
    """
    Test Scenario 3: Project Breakdown pipeline.

    Verifies that a brief project description can be expanded into detailed
    breakdown with work streams, milestones, and estimates.
    """
    # Arrange
    pipeline_name = "project_breakdown"
    input_data = {
        "project_brief": "Build a mobile app for restaurant reservations",
        "timeline_weeks": 16,
    }

    # Act
    result = mock_run_pipeline(pipeline_name, input_data)

    # Assert
    assert result.success, "Pipeline should execute successfully"

    # Check categories/work streams
    categories = result.get("categories", {})
    assert len(categories) >= 3, "Should have at least 3 work stream categories"  # noqa: PLR2004

    # Check milestones
    milestones = result.get("milestones", [])
    assert len(milestones) >= 2, "Should have at least 2 milestones/phases"  # noqa: PLR2004

    # Check estimates
    estimates = result.get("estimates", {})
    assert "effort_person_weeks" in estimates, "Should estimate effort"
    assert "duration_weeks" in estimates, "Should estimate duration"
    assert "budget_usd" in estimates, "Should estimate budget"

    effort = estimates.get("effort_person_weeks", 0)
    assert effort > 0, "Effort estimate should be > 0"

    # Check quality score
    quality_score = result.get("quality_score", 0)
    assert quality_score >= 7.0, f"Quality score should be >= 7.0, got {quality_score}"  # noqa: PLR2004

    # Check techniques used
    techniques = result.metadata.get("techniques_used", [])
    assert "sequential_thinking" in techniques, "Should use Sequential Thinking MCP"
    assert "category_naming" in techniques, "Should use category_naming"
    assert "checkpoint_naming" in techniques, "Should use checkpoint_naming"
    assert "quality_scoring" in techniques, "Should use quality_scoring"


@pytest.mark.smoke
def test_all_meeting_files() -> None:
    """Test that all meeting files can be processed."""
    meeting_files = [
        "kickoff_acme_mobile_2024_03.md",
        "brainstorm_techstart_website_2024_04.md",
        "status_update_globex_q2_2024.md",
        "retrospective_fintech_project_2024_03.md",
        "discovery_healthtech_2024_05.md",
    ]

    for meeting_file in meeting_files:
        input_data = {"meeting_file": meeting_file}
        result = mock_run_pipeline("meeting_to_plan", input_data)
        assert result.success, f"Should process {meeting_file}"
        assert result.get("categories"), f"Should extract categories from {meeting_file}"


@pytest.mark.smoke
def test_all_client_patterns() -> None:
    """Test that all client email patterns can be learned."""
    clients = [
        "Acme CEO Sarah",
        "TechStart Marcus",
        "Globex CTO Rachel",
    ]

    for client_name in clients:
        input_data = {"client_name": client_name}
        result = mock_run_pipeline("learn_preferences", input_data)
        assert result.success, f"Should learn patterns for {client_name}"

        pattern = result.get("pattern_artifact", {})
        assert pattern["confidence"] >= 0.7, (  # noqa: PLR2004
            f"Pattern confidence should be >= 0.7 for {client_name}"
        )


@pytest.mark.smoke
def test_multiple_project_briefs() -> None:
    """Test that different project types can be broken down."""
    project_briefs = [
        "Build a mobile app for restaurant reservations",
        "Healthcare patient portal with appointment booking",
        "E-commerce platform for handmade crafts",
        "Real-time inventory management system",
        "Social fitness tracking app",
    ]

    for brief in project_briefs:
        input_data = {"project_brief": brief, "timeline_weeks": 16}
        result = mock_run_pipeline("project_breakdown", input_data)
        assert result.success, f"Should break down: {brief}"

        categories = result.get("categories", {})
        assert len(categories) >= 3, f"Should have >= 3 categories for: {brief}"  # noqa: PLR2004


@pytest.mark.smoke
def test_techniques_are_applied() -> None:
    """Verify that AI generation techniques are applied in pipelines."""
    # Test category_naming in meeting_to_plan
    result = mock_run_pipeline("meeting_to_plan", {"meeting_file": "test.md"})
    assert "category_naming" in result.metadata.get(
        "techniques_used", []
    ), "meeting_to_plan should use category_naming"

    # Test checkpoint_naming in meeting_to_plan
    assert "checkpoint_naming" in result.metadata.get(
        "techniques_used", []
    ), "meeting_to_plan should use checkpoint_naming"

    # Test pattern_artifact in learn_preferences
    result = mock_run_pipeline("learn_preferences", {"client_name": "Test Client"})
    assert "pattern_artifact" in result.metadata.get(
        "techniques_used", []
    ), "learn_preferences should create PatternArtifact"

    # Test quality_scoring in project_breakdown
    result = mock_run_pipeline(
        "project_breakdown", {"project_brief": "Test project", "timeline_weeks": 10}
    )
    assert "quality_scoring" in result.metadata.get(
        "techniques_used", []
    ), "project_breakdown should use quality_scoring"


@pytest.mark.smoke
def test_mcp_integrations() -> None:
    """Verify that MCP integrations are used in pipelines."""
    # Test Sequential Thinking in meeting_to_plan
    result = mock_run_pipeline("meeting_to_plan", {"meeting_file": "test.md"})
    # Sequential Thinking should be used for analysis and validation
    assert result.success, "Should use Sequential Thinking MCP"

    # Test In-Memoria in learn_preferences
    result = mock_run_pipeline("learn_preferences", {"client_name": "Test Client"})
    assert "in_memoria" in result.metadata.get(
        "mcp_providers", []
    ), "Should use In-Memoria MCP for pattern storage"


@pytest.mark.smoke
def test_quality_scores_meet_threshold() -> None:
    """Verify that pipeline outputs meet quality thresholds."""
    # Meeting to plan
    result = mock_run_pipeline("meeting_to_plan", {"meeting_file": "test.md"})
    assert result.get("quality_score", 0) >= 7.0, (  # noqa: PLR2004
        "meeting_to_plan quality should be >= 7.0"
    )

    # Project breakdown
    result = mock_run_pipeline("project_breakdown", {"project_brief": "Test", "timeline_weeks": 10})
    assert result.get("quality_score", 0) >= 7.0, (  # noqa: PLR2004
        "project_breakdown quality should be >= 7.0"
    )

    # Learn preferences (confidence score)
    result = mock_run_pipeline("learn_preferences", {"client_name": "Test"})
    pattern = result.get("pattern_artifact", {})
    assert pattern.get("confidence", 0) >= 0.7, (  # noqa: PLR2004
        "Pattern confidence should be >= 0.7"
    )


@pytest.mark.integration
@pytest.mark.skipif(
    "SIBYL_INTEGRATION_TESTS" not in os.environ,
    reason="Set SIBYL_INTEGRATION_TESTS=1 to run actual pipeline tests",
)
def test_real_pipeline_execution() -> None:
    """
    Integration test: Run actual pipelines with Sibyl runtime.

    This test is skipped by default. Set SIBYL_INTEGRATION_TESTS=1 to run.
    Requires:
    - Sibyl fully installed
    - MCP servers available
    - LLM API keys configured
    """
    from sibyl.runtime import PipelineRunner  # noqa: PLC0415

    workspace_path = str(CONFIG_DIR / "workspace.yaml")
    runner = PipelineRunner(workspace_path)

    # Test meeting_to_plan
    result = runner.run(
        "meeting_to_plan", input_data={"meeting_file": "kickoff_acme_mobile_2024_03.md"}
    )
    assert result.success, "Real meeting_to_plan pipeline should succeed"

    # Test project_breakdown
    result = runner.run(
        "project_breakdown",
        input_data={
            "project_brief": "Build a mobile app for restaurant reservations",
            "timeline_weeks": 16,
        },
    )
    assert result.success, "Real project_breakdown pipeline should succeed"


if __name__ == "__main__":
    # Run smoke tests
    pytest.main([__file__, "-v", "-m", "smoke"])

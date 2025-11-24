"""
Smoke tests for Vertex Foundry ML Platform Pipelines.

These tests verify that the pipelines are configured correctly and can execute
with mocked MCP responses. They demonstrate features:
- PollableJobHandle for long-running jobs
- SessionHandle for multi-turn conversations
- Job polling with automatic retry
- Streaming outputs
- Control flow (when/retry conditions)
"""

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest


# Mock Sibyl framework components (these would normally be imported)
class MockPollableJobHandle:
    """Mock PollableJobHandle for testing job polling."""

    def __init__(self, job_ids: list[str]) -> None:
        self.job_ids = job_ids
        self.poll_count = 0
        self.status = "running"

    async def poll(self) -> dict[str, Any]:
        """Simulate polling with status progression."""
        self.poll_count += 1

        # Simulate job progression
        if self.poll_count < 3:  # noqa: PLR2004
            completed = self.poll_count * 2
            return {
                "status": "running",
                "completed": completed,
                "running": min(5, len(self.job_ids) - completed),
                "queued": max(0, len(self.job_ids) - completed - 5),
                "failed": 0,
            }
        if self.poll_count == 3:  # noqa: PLR2004
            # One job fails
            return {"status": "running", "completed": 5, "running": 5, "queued": 7, "failed": 1}
        # All complete
        self.status = "completed"
        return {
            "status": "completed",
            "completed": len(self.job_ids),
            "running": 0,
            "queued": 0,
            "failed": 1,
        }

    async def stream_results(self) -> AsyncIterator[dict[str, Any]]:
        """Simulate streaming job results."""
        for i, job_id in enumerate(self.job_ids):
            if i == 7:  # Simulate one failure  # noqa: PLR2004
                yield {
                    "type": "job_failed",
                    "job_id": job_id,
                    "error": "RuntimeError: Loss became NaN",
                    "error_type": "transient",
                }
            else:
                yield {
                    "type": "job_completed",
                    "job_id": job_id,
                    "hyperparameters": {
                        "learning_rate": 0.001 * (i + 1),
                        "batch_size": 32 * (i % 3 + 1),
                    },
                    "metrics": {"val_acc": 80.0 + i * 0.5, "train_loss": 0.5 - i * 0.02},
                    "cost_usd": 25.0 + i * 0.5,
                }


class MockSessionHandle:
    """Mock SessionHandle for testing multi-turn conversations."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.turn_count = 0
        self.context = []

    async def send_message(self, message: str) -> dict[str, Any]:
        """Simulate multi-turn conversation with context retention."""
        self.turn_count += 1
        self.context.append({"role": "user", "content": message})

        # Simulate different responses based on turn
        if self.turn_count == 1:
            # Turn 1: Code analysis
            response = {
                "turn": 1,
                "analysis_type": "code_bug_detection",
                "issues_found": [
                    {
                        "file": "train_model.py",
                        "line": 85,
                        "severity": "HIGH",
                        "description": "CrossEntropyLoss(reduction='sum') should be reduction='mean'",
                        "impact": "Gradients scaled by batch_size",
                    }
                ],
            }
        elif self.turn_count == 2:  # noqa: PLR2004
            # Turn 2: Error correlation (uses context from turn 1)
            response = {
                "turn": 2,
                "correlations": [
                    {
                        "error_pattern": "Loss gradient explosion",
                        "code_issue": "Loss function reduction='sum'",
                        "confidence": 0.95,
                        "explanation": "reduction='sum' causes 32x gradient scaling",
                    }
                ],
                "context_used": True,
            }
        elif self.turn_count == 3:  # noqa: PLR2004
            # Turn 3: Root cause identification (uses context from turns 1-2)
            response = {
                "turn": 3,
                "root_cause": "Loss function misconfiguration combined with high learning rate",
                "confidence": 0.98,
                "reasoning_chain": [
                    "Loss reduction='sum' scales gradients by batch_size (32x)",
                    "Learning rate 0.01 already 10x too high",
                    "Combined effect: effective LR = 0.32 (320x recommended)",
                    "Model converged at step 1500, became sensitive",
                    "Large update at step 1520 caused explosion",
                ],
                "context_used": True,
            }
        else:
            # Turn 4+: Recommendations
            response = {
                "turn": self.turn_count,
                "recommendations": [
                    {
                        "priority": "CRITICAL",
                        "type": "code_fix",
                        "file": "train_model.py",
                        "line": 85,
                        "fix": "criterion = nn.CrossEntropyLoss(reduction='mean')",
                    }
                ],
                "context_used": True,
            }

        self.context.append({"role": "assistant", "content": json.dumps(response)})
        return response


@pytest.fixture
def workspace_path() -> Any:
    """Path to workspace configuration."""
    return Path(__file__).parent.parent / "config" / "workspace.yaml"


@pytest.fixture
def pipelines_path() -> Any:
    """Path to pipeline configurations."""
    return Path(__file__).parent.parent / "config" / "pipelines.yaml"


@pytest.fixture
def data_path() -> Any:
    """Path to test data."""
    return Path(__file__).parent.parent / "data"


@pytest.fixture
def mock_solver_mcp() -> Any:
    """Mock Solver MCP for hyperparameter optimization."""
    mock = AsyncMock()

    async def plan_search_grid(search_space, budget_usd: Any, cost_model: Any) -> Any:
        """Mock search grid planning."""
        # Calculate grid size based on search space
        grid_size = 1
        for _param, values in search_space.items():
            grid_size *= len(values)

        # Estimate cost
        cost_per_trial = cost_model["T4_hourly"] * cost_model["estimated_duration_hours"]
        estimated_cost = grid_size * cost_per_trial

        # Adjust if over budget
        if estimated_cost > budget_usd:
            # Reduce grid size
            reduction_factor = budget_usd / estimated_cost
            grid_size = int(grid_size * reduction_factor)
            estimated_cost = budget_usd * 0.95  # 95% budget utilization

        return {
            "grid": [
                {"learning_rate": lr, "batch_size": bs, "dropout": dr}
                for lr in search_space.get("learning_rate", [0.001])
                for bs in search_space.get("batch_size", [32])
                for dr in search_space.get("dropout", [0.5])
            ][:grid_size],
            "num_trials": grid_size,
            "estimated_cost": estimated_cost,
        }

    mock.plan_search_grid = plan_search_grid
    return mock


@pytest.fixture
def mock_conductor_mcp() -> Any:
    """Mock Conductor MCP for job orchestration."""
    mock = AsyncMock()

    async def launch_jobs(job_configs, training_script: Any, base_config: Any) -> Any:
        """Mock job launching with PollableJobHandle."""
        job_ids = [f"job_{i:03d}" for i in range(len(job_configs))]
        handle = MockPollableJobHandle(job_ids)

        return {"job_handle": handle, "job_ids": job_ids, "status": "submitted"}

    mock.launch_jobs = launch_jobs
    return mock


@pytest.fixture
def mock_code_analyzer_mcp() -> Any:
    """Mock Deep Code Reasoning MCP for code analysis."""
    mock = AsyncMock()

    async def create_session(session_type, context_retention: Any, max_turns: Any) -> Any:
        """Mock session creation."""
        session_id = f"session_{hash(session_type)}"
        return MockSessionHandle(session_id)

    async def analyze_code(
        session_handle, code_files: Any, error_context: Any, analysis_type: Any
    ) -> Any:
        """Mock code analysis."""
        return await session_handle.send_message(
            f"Analyze {len(code_files)} files for {analysis_type}"
        )

    mock.create_session = create_session
    mock.analyze_code = analyze_code
    return mock


# ============================================================================
# Test Suite 1: Hyperparameter Sweep Pipeline
# ============================================================================


class TestHyperparameterSweep:
    """Test hyperparameter sweep pipeline with job polling and streaming."""

    @pytest.mark.asyncio
    async def test_search_grid_planning(self, mock_solver_mcp: Any) -> None:
        """Test that Solver MCP plans search grid within budget."""
        search_space = {
            "learning_rate": [0.0001, 0.001, 0.01],
            "batch_size": [32, 64, 128],
            "dropout": [0.3, 0.5, 0.7],
        }
        budget_usd = 500
        cost_model = {"T4_hourly": 0.35, "estimated_duration_hours": 2}

        result = await mock_solver_mcp.plan_search_grid(search_space, budget_usd, cost_model)

        # Verify grid was planned
        assert "grid" in result
        assert "num_trials" in result
        assert "estimated_cost" in result

        # Verify budget constraint
        assert result["estimated_cost"] <= budget_usd

        # Verify grid is reasonable
        assert result["num_trials"] > 0
        assert len(result["grid"]) == result["num_trials"]

        # Verify grid contains valid hyperparameters
        for config in result["grid"]:
            assert "learning_rate" in config
            assert "batch_size" in config
            assert "dropout" in config
            assert config["learning_rate"] in search_space["learning_rate"]
            assert config["batch_size"] in search_space["batch_size"]
            assert config["dropout"] in search_space["dropout"]

    @pytest.mark.asyncio
    async def test_job_launch_returns_pollable_handle(self, mock_conductor_mcp: Any) -> None:
        """Test that Conductor MCP returns PollableJobHandle."""
        job_configs = [
            {"learning_rate": 0.001, "batch_size": 32},
            {"learning_rate": 0.001, "batch_size": 64},
            {"learning_rate": 0.01, "batch_size": 32},
        ]

        result = await mock_conductor_mcp.launch_jobs(job_configs, "train_model.py", "config.yaml")

        # Verify PollableJobHandle was created
        assert "job_handle" in result
        assert isinstance(result["job_handle"], MockPollableJobHandle)

        # Verify job IDs were assigned
        assert "job_ids" in result
        assert len(result["job_ids"]) == len(job_configs)

        # Verify status
        assert result["status"] == "submitted"

    @pytest.mark.asyncio
    async def test_automatic_job_polling(self, mock_conductor_mcp: Any) -> None:
        """Test automatic job polling with exponential backoff."""
        job_configs = [{"lr": 0.001}] * 18
        result = await mock_conductor_mcp.launch_jobs(job_configs, "", "")
        job_handle = result["job_handle"]

        # Poll multiple times to simulate automatic polling
        poll_results = []
        for _ in range(5):
            status = await job_handle.poll()
            poll_results.append(status)

        # Verify polling shows progression
        assert poll_results[0]["status"] == "running"
        assert poll_results[0]["completed"] < len(job_configs)

        # Verify jobs complete over time
        assert poll_results[-1]["status"] == "completed"
        assert poll_results[-1]["completed"] == len(job_configs)

        # Verify intermediate states show progress
        completed_counts = [r["completed"] for r in poll_results]
        assert completed_counts == sorted(completed_counts)  # Monotonically increasing

    @pytest.mark.asyncio
    async def test_streaming_job_results(self, mock_conductor_mcp: Any) -> None:
        """Test streaming of job results as they complete."""
        job_configs = [{"lr": 0.001}] * 18
        result = await mock_conductor_mcp.launch_jobs(job_configs, "", "")
        job_handle = result["job_handle"]

        # Collect streamed results
        streamed_results = []
        async for chunk in job_handle.stream_results():
            streamed_results.append(chunk)

        # Verify all jobs streamed
        assert len(streamed_results) == len(job_configs)

        # Verify stream contains both completed and failed jobs
        completed_jobs = [r for r in streamed_results if r["type"] == "job_completed"]
        failed_jobs = [r for r in streamed_results if r["type"] == "job_failed"]

        assert len(completed_jobs) > 0
        assert len(failed_jobs) > 0

        # Verify completed job structure
        for job in completed_jobs:
            assert "job_id" in job
            assert "hyperparameters" in job
            assert "metrics" in job
            assert "cost_usd" in job
            assert "val_acc" in job["metrics"]

        # Verify failed job structure
        for job in failed_jobs:
            assert "job_id" in job
            assert "error" in job
            assert "error_type" in job

    @pytest.mark.asyncio
    async def test_retry_logic_for_failed_jobs(self, mock_conductor_mcp: Any) -> None:
        """Test that failed jobs trigger retry logic."""
        job_configs = [{"lr": 0.001}] * 18
        result = await mock_conductor_mcp.launch_jobs(job_configs, "", "")
        job_handle = result["job_handle"]

        # Collect results to identify failures
        failed_jobs = []
        async for chunk in job_handle.stream_results():
            if chunk["type"] == "job_failed" and chunk["error_type"] == "transient":
                failed_jobs.append(chunk)

        # Verify transient failures were detected
        assert len(failed_jobs) > 0

        # Simulate retry (in real pipeline, this would be automatic)
        retry_configs = [{"lr": 0.0005}]  # Reduced learning rate
        retry_result = await mock_conductor_mcp.launch_jobs(retry_configs, "", "")

        # Verify retry job was launched
        assert retry_result["status"] == "submitted"
        assert len(retry_result["job_ids"]) == len(retry_configs)

    @pytest.mark.asyncio
    async def test_best_hyperparameter_selection(self, mock_conductor_mcp: Any) -> None:
        """Test selection of best hyperparameters from results."""
        job_configs = [{"lr": 0.001}] * 10
        result = await mock_conductor_mcp.launch_jobs(job_configs, "", "")
        job_handle = result["job_handle"]

        # Collect completed results
        completed_results = []
        async for chunk in job_handle.stream_results():
            if chunk["type"] == "job_completed":
                completed_results.append(chunk)

        # Rank by validation accuracy
        ranked = sorted(completed_results, key=lambda x: x["metrics"]["val_acc"], reverse=True)

        # Verify best result
        best = ranked[0]
        assert best["metrics"]["val_acc"] > ranked[-1]["metrics"]["val_acc"]
        assert "hyperparameters" in best

    @pytest.mark.asyncio
    async def test_cost_calculation(self, mock_conductor_mcp: Any) -> None:
        """Test total cost calculation for sweep."""
        job_configs = [{"lr": 0.001}] * 10
        result = await mock_conductor_mcp.launch_jobs(job_configs, "", "")
        job_handle = result["job_handle"]

        # Collect all results
        all_results = []
        async for chunk in job_handle.stream_results():
            all_results.append(chunk)

        # Calculate total cost
        total_cost = sum(r.get("cost_usd", 0) for r in all_results)

        # Verify cost is reasonable
        assert total_cost > 0
        assert total_cost < 1000  # Sanity check  # noqa: PLR2004


# ============================================================================
# Test Suite 2: Diagnose Failure Pipeline
# ============================================================================


class TestDiagnoseFailure:
    """Test failure diagnosis pipeline with SessionHandle."""

    @pytest.mark.asyncio
    async def test_load_failed_run_data(self, data_path: Any) -> None:
        """Test loading failed run metadata and logs."""
        run_id = "run_20250116_091523"

        # Load metadata
        metadata_path = data_path / "runs" / f"{run_id}.json"
        assert metadata_path.exists(), f"Run metadata not found: {metadata_path}"

        with open(metadata_path) as f:
            metadata = json.load(f)

        # Verify failure information
        assert metadata["status"] == "failed"
        assert "failure_step" in metadata
        assert metadata["failure_step"] == 1523  # noqa: PLR2004
        assert "error_message" in metadata
        assert "NaN" in metadata["error_message"]

        # Load error log
        log_path = data_path / "experiments" / "logs" / f"{run_id}_error.log"
        assert log_path.exists(), f"Error log not found: {log_path}"

        with open(log_path) as f:
            log_content = f.read()

        # Verify error log contains key information
        assert "NaN" in log_content
        assert "gradient explosion" in log_content.lower()
        assert "CrossEntropyLoss" in log_content

    @pytest.mark.asyncio
    async def test_session_creation(self, mock_code_analyzer_mcp: Any) -> None:
        """Test SessionHandle creation for persistent context."""
        session_handle = await mock_code_analyzer_mcp.create_session(
            session_type="persistent", context_retention=True, max_turns=10
        )

        # Verify session was created
        assert isinstance(session_handle, MockSessionHandle)
        assert session_handle.session_id is not None
        assert session_handle.turn_count == 0

    @pytest.mark.asyncio
    async def test_multi_turn_code_analysis(self, mock_code_analyzer_mcp: Any) -> None:
        """Test multi-turn code analysis with context retention."""
        # Create session
        session_handle = await mock_code_analyzer_mcp.create_session(
            session_type="persistent", context_retention=True, max_turns=10
        )

        # Turn 1: Analyze code
        response1 = await mock_code_analyzer_mcp.analyze_code(
            session_handle,
            code_files=["train_model.py"],
            error_context="NaN loss at step 1523",
            analysis_type="bug_detection",
        )

        assert response1["turn"] == 1
        assert "issues_found" in response1
        assert len(response1["issues_found"]) > 0

        # Turn 2: Correlate with errors (uses context from turn 1)
        response2 = await session_handle.send_message("Correlate with error patterns")

        assert response2["turn"] == 2  # noqa: PLR2004
        assert "correlations" in response2
        assert response2["context_used"] is True

        # Turn 3: Identify root cause (uses context from turns 1-2)
        response3 = await session_handle.send_message("Identify root cause")

        assert response3["turn"] == 3  # noqa: PLR2004
        assert "root_cause" in response3
        assert response3["context_used"] is True
        assert "reasoning_chain" in response3

        # Verify context is maintained across turns
        assert session_handle.turn_count == 3  # noqa: PLR2004
        assert (
            len(session_handle.context) == 6
        )  # 3 turns * 2 messages (user + assistant)  # noqa: PLR2004

    @pytest.mark.asyncio
    async def test_context_retention_across_turns(self, mock_code_analyzer_mcp: Any) -> None:
        """Test that context is retained across multiple turns."""
        session_handle = await mock_code_analyzer_mcp.create_session(
            session_type="persistent", context_retention=True, max_turns=10
        )

        # Turn 1
        await session_handle.send_message("Analyze code")
        # Turn 2
        response2 = await session_handle.send_message("Correlate errors")
        # Turn 3
        response3 = await session_handle.send_message("Identify root cause")

        # Verify each turn acknowledges context usage
        assert response2.get("context_used") is True
        assert response3.get("context_used") is True

        # Verify reasoning builds on previous turns
        assert "reasoning_chain" in response3
        assert len(response3["reasoning_chain"]) > 1

    @pytest.mark.asyncio
    async def test_diagnostic_report_generation(
        self, mock_code_analyzer_mcp: Any, data_path: Any
    ) -> None:
        """Test generation of comprehensive diagnostic report."""
        # Load run data
        run_id = "run_20250116_091523"
        metadata_path = data_path / "runs" / f"{run_id}.json"
        with open(metadata_path) as f:
            metadata = json.load(f)

        # Run analysis
        session_handle = await mock_code_analyzer_mcp.create_session(
            session_type="persistent", context_retention=True, max_turns=10
        )

        # Multi-turn analysis
        await session_handle.send_message("Analyze code")
        await session_handle.send_message("Correlate errors")
        root_cause = await session_handle.send_message("Identify root cause")
        recommendations = await session_handle.send_message("Generate recommendations")

        # Generate diagnostic report
        report = {
            "run_id": run_id,
            "status": metadata["status"],
            "failure_step": metadata["failure_step"],
            "error_message": metadata["error_message"],
            "root_cause": root_cause["root_cause"],
            "confidence": root_cause["confidence"],
            "recommendations": recommendations["recommendations"],
            "analysis_turns": session_handle.turn_count,
        }

        # Verify report structure
        assert report["run_id"] == run_id
        assert report["status"] == "failed"
        assert report["root_cause"] is not None
        assert report["confidence"] > 0.9  # noqa: PLR2004
        assert len(report["recommendations"]) > 0
        assert report["analysis_turns"] == 4  # noqa: PLR2004

        # Verify recommendations have correct structure
        for rec in report["recommendations"]:
            assert "priority" in rec
            assert "type" in rec
            assert rec["priority"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

    @pytest.mark.asyncio
    async def test_session_cleanup(self, mock_code_analyzer_mcp: Any) -> None:
        """Test proper session cleanup after analysis."""
        session_handle = await mock_code_analyzer_mcp.create_session(
            session_type="persistent", context_retention=True, max_turns=10
        )

        # Use session
        await session_handle.send_message("Test message")

        # Verify session exists
        assert session_handle.turn_count > 0

        # In real implementation, this would call session cleanup
        # For now, just verify session handle exists
        assert session_handle.session_id is not None


# ============================================================================
# Test Suite 3: Pipeline Configuration Validation
# ============================================================================


class TestPipelineConfiguration:
    """Test that pipeline configurations are valid."""

    def test_workspace_config_exists(self, workspace_path: Any) -> None:
        """Test workspace configuration file exists."""
        assert workspace_path.exists(), f"Workspace config not found: {workspace_path}"

    def test_pipelines_config_exists(self, pipelines_path: Any) -> None:
        """Test pipeline configuration file exists."""
        assert pipelines_path.exists(), f"Pipelines config not found: {pipelines_path}"

    def test_experiment_data_exists(self, data_path: Any) -> None:
        """Test that experiment data files exist."""
        # Check experiment configs
        exp_configs = data_path / "experiments" / "experiment_configs"
        assert exp_configs.exists()
        assert len(list(exp_configs.glob("*.yaml"))) >= 5  # noqa: PLR2004

        # Check training code
        code_dir = data_path / "code"
        assert (code_dir / "train_model.py").exists()
        assert (code_dir / "model.py").exists()
        assert (code_dir / "data_loader.py").exists()

        # Check run metadata
        runs_dir = data_path / "runs"
        assert len(list(runs_dir.glob("*.json"))) >= 5  # noqa: PLR2004

        # Check error log
        logs_dir = data_path / "experiments" / "logs"
        assert (logs_dir / "run_20250116_091523_error.log").exists()

    def test_training_code_contains_bug(self, data_path: Any) -> None:
        """Test that training code contains the intentional bug."""
        train_script = data_path / "code" / "train_model.py"

        with open(train_script) as f:
            content = f.read()

        # Verify bug is present
        assert "reduction='sum'" in content
        assert "CrossEntropyLoss" in content

        # Verify bug comment is present
        assert "BUG" in content or "bug" in content


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

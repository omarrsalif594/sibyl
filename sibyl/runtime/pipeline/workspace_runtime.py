"""Workspace runtime for executing shops and pipelines.

This module provides the core runtime infrastructure for Sibyl:
- ShopRuntime: Manages and executes techniques within a shop
- WorkspaceRuntime: Orchestrates pipeline execution across shops

Example:
    from sibyl.workspace import load_workspace
    from sibyl.runtime.providers import build_providers
    from sibyl.runtime import WorkspaceRuntime

    # Load workspace and build providers
    workspace = load_workspace("config/workspaces/example_local.yaml")
    providers = build_providers(workspace)

    # Create runtime and execute pipeline
    runtime = WorkspaceRuntime(workspace, providers)
    result = await runtime.run_pipeline("web_research_pipeline", query="What is Sibyl?")
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from sibyl.core.pipeline.condition_evaluator import ConditionEvaluationError, ConditionEvaluator
from sibyl.core.pipeline.template_engine import PipelineTemplateEngine
from sibyl.runtime.pipeline.errors import BudgetExceededError, StepTimeoutError
from sibyl.runtime.providers.registry import ProviderRegistry
from sibyl.techniques.protocols import BaseTechnique
from sibyl.techniques.registry import get_technique, technique_exists
from sibyl.workspace.schema import (
    BudgetConfig,
    LoopConfig,
    ParallelConfig,
    PipelineConfig,
    PipelineStepConfig,
    ShopConfig,
    TryConfig,
    WorkspaceSettings,
)

logger = logging.getLogger(__name__)


@dataclass
class BudgetTracker:
    """Tracks resource usage against budget limits.

    Maintains running totals of cost, tokens, and requests at different
    scopes (step, pipeline, global) and checks against configured limits.

    Attributes:
        total_cost_usd: Running total of cost in USD
        total_tokens: Running total of tokens (input + output)
        total_requests: Running total of LLM requests
        step_cost_usd: Cost for current step
        step_tokens: Tokens for current step
        step_requests: Requests for current step
    """

    total_cost_usd: float = 0.0
    total_tokens: int = 0
    total_requests: int = 0
    step_cost_usd: float = 0.0
    step_tokens: int = 0
    step_requests: int = 0

    def reset_step(self) -> None:
        """Reset step-level counters."""
        self.step_cost_usd = 0.0
        self.step_tokens = 0
        self.step_requests = 0

    def record_llm_call(
        self,
        cost_usd: float = 0.0,
        tokens: int = 0,
    ) -> None:
        """Record an LLM call with its cost and token usage.

        Args:
            cost_usd: Cost of the call in USD
            tokens: Number of tokens used (input + output)
        """
        self.total_cost_usd += cost_usd
        self.total_tokens += tokens
        self.total_requests += 1
        self.step_cost_usd += cost_usd
        self.step_tokens += tokens
        self.step_requests += 1

        logger.debug(
            f"Recorded LLM call: cost=${cost_usd:.4f}, tokens={tokens}, "
            f"total_cost=${self.total_cost_usd:.4f}, total_tokens={self.total_tokens}"
        )

    def check_budget(
        self,
        budget: BudgetConfig | None,
        scope: str,
        use_step_totals: bool = False,
    ) -> None:
        """Check if budget limits would be exceeded.

        Args:
            budget: Budget configuration to check against
            scope: Scope name for error messages (step, pipeline, global)
            use_step_totals: If True, check step totals; otherwise check global totals

        Raises:
            BudgetExceededError: If any budget limit is exceeded
        """
        if budget is None:
            return

        cost = self.step_cost_usd if use_step_totals else self.total_cost_usd
        tokens = self.step_tokens if use_step_totals else self.total_tokens
        requests = self.step_requests if use_step_totals else self.total_requests

        if budget.max_cost_usd is not None and cost > budget.max_cost_usd:
            raise BudgetExceededError(
                budget_type="cost",
                limit=budget.max_cost_usd,
                actual=cost,
                scope=scope,
            )

        if budget.max_tokens is not None and tokens > budget.max_tokens:
            raise BudgetExceededError(
                budget_type="tokens",
                limit=budget.max_tokens,
                actual=tokens,
                scope=scope,
            )

        if budget.max_requests is not None and requests > budget.max_requests:
            raise BudgetExceededError(
                budget_type="requests",
                limit=budget.max_requests,
                actual=requests,
                scope=scope,
            )


class TechniqueResolutionError(Exception):
    """Raised when a technique cannot be resolved or loaded."""


class PipelineExecutionError(Exception):
    """Raised when pipeline execution fails."""

    def __init__(self, message: str, cancelled: bool = False) -> None:
        """Initialize pipeline execution error.

        Args:
            message: Error message
            cancelled: True if error is due to cancellation
        """
        super().__init__(message)
        self.cancelled = cancelled


@dataclass
class TechniqueReference:
    """Parsed reference to a technique implementation.

    Attributes:
        module_path: Base module path (e.g., "rag_pipeline.chunking")
        technique_name: Technique name for registry lookup (e.g., "chunking")
        implementation: Implementation/subtechnique name (e.g., "semantic")
    """

    module_path: str
    technique_name: str
    implementation: str

    @classmethod
    def parse(cls, reference: str) -> "TechniqueReference":
        """Parse a technique reference string.

        Format: "category.technique:implementation"
        Example: "rag_pipeline.chunking:semantic"

        Args:
            reference: Technique reference string

        Returns:
            Parsed TechniqueReference

        Raises:
            ValueError: If reference format is invalid
        """
        if ":" not in reference:
            msg = (
                f"Invalid technique reference '{reference}': must be in format "
                "'category.technique:implementation'"
            )
            raise ValueError(msg)

        module_path, implementation = reference.rsplit(":", 1)

        # Extract technique name from module path
        # e.g., "rag_pipeline.chunking" -> "chunking"
        technique_name = module_path.split(".")[-1] if "." in module_path else module_path

        return cls(
            module_path=module_path,
            technique_name=technique_name,
            implementation=implementation,
        )


class ShopRuntime:
    """Runtime for executing techniques within a shop.

    A shop runtime is responsible for:
    - Loading and caching technique instances
    - Resolving technique references to implementations
    - Executing techniques with appropriate configuration

    Attributes:
        name: Shop name
        config: Shop configuration
        providers: Provider registry for accessing LLM, embeddings, etc.
    """

    def __init__(
        self,
        name: str,
        shop_cfg: ShopConfig,
        providers: ProviderRegistry,
    ) -> None:
        """Initialize shop runtime.

        Args:
            name: Shop name
            shop_cfg: Shop configuration
            providers: Provider registry
        """
        self.name = name
        self.config = shop_cfg
        self.providers = providers
        self._technique_cache: dict[str, BaseTechnique] = {}

        logger.debug(f"Initialized ShopRuntime '{name}' with {len(shop_cfg.techniques)} techniques")

    def _resolve_technique(self, logical_name: str) -> TechniqueReference:
        """Resolve a logical technique name to its implementation.

        Args:
            logical_name: Logical name from shop config (e.g., "chunker")

        Returns:
            Parsed technique reference

        Raises:
            TechniqueResolutionError: If technique not found or invalid
        """
        if logical_name not in self.config.techniques:
            available = ", ".join(self.config.techniques.keys())
            msg = (
                f"Technique '{logical_name}' not found in shop '{self.name}'. "
                f"Available techniques: {available}"
            )
            raise TechniqueResolutionError(msg)

        reference_str = self.config.techniques[logical_name]

        try:
            return TechniqueReference.parse(reference_str)
        except ValueError as e:
            msg = f"Failed to parse technique reference for '{logical_name}': {e}"
            raise TechniqueResolutionError(msg) from e

    def _load_technique(self, reference: TechniqueReference) -> BaseTechnique:
        """Load a technique instance from the registry.

        Args:
            reference: Parsed technique reference

        Returns:
            Technique instance

        Raises:
            TechniqueResolutionError: If technique cannot be loaded
        """
        # Check if we've already loaded this technique
        cache_key = reference.technique_name
        if cache_key in self._technique_cache:
            logger.debug("Using cached technique: %s", cache_key)
            return self._technique_cache[cache_key]

        # Check if technique exists in registry
        if not technique_exists(reference.technique_name):
            msg = (
                f"Technique '{reference.technique_name}' not found in registry. "
                f"Module path: {reference.module_path}"
            )
            raise TechniqueResolutionError(msg)

        try:
            # Load technique from registry
            technique = get_technique(reference.technique_name, cached=True)
            self._technique_cache[cache_key] = technique

            logger.info("Loaded technique '%s' for shop '%s'", reference.technique_name, self.name)

            return technique

        except Exception as e:
            msg = f"Failed to load technique '{reference.technique_name}': {e}"
            raise TechniqueResolutionError(msg) from e

    async def run_technique(
        self,
        logical_name: str,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a technique by its logical name.

        Args:
            logical_name: Logical technique name (e.g., "chunker")
            context: Shared context dictionary for pipeline execution
            **kwargs: Additional arguments passed to technique

        Returns:
            Dictionary with execution results

        Raises:
            TechniqueResolutionError: If technique cannot be resolved
            RuntimeError: If technique execution fails
        """
        # Resolve technique reference
        reference = self._resolve_technique(logical_name)

        # Load technique instance
        technique = self._load_technique(reference)

        # Merge configuration
        config = {}
        if self.config.config:
            config.update(self.config.config)
        if "config" in kwargs:
            config.update(kwargs.pop("config"))

        # Prepare input data
        if context is None:
            context = {}

        input_data = kwargs.get("input_data", context.get("input_data"))

        try:
            logger.info(
                "Executing technique '%s' (implementation: %s) in shop '%s'",
                logical_name,
                reference.implementation,
                self.name,
            )

            # Execute technique
            # Note: BaseTechnique.execute is synchronous, but we wrap in async
            # for future async support
            result = technique.execute(
                input_data=input_data,
                subtechnique=reference.implementation,
                config=config,
                **kwargs,
            )

            logger.debug("Technique '%s' completed successfully", logical_name)

            return {"result": result, "success": True}

        except Exception as e:
            logger.exception("Technique '%s' failed: %s", logical_name, e)
            msg = f"Technique '{logical_name}' execution failed: {e}"
            raise RuntimeError(msg) from e

    def list_techniques(self) -> list[str]:
        """List all available technique names in this shop.

        Returns:
            List of logical technique names
        """
        return list(self.config.techniques.keys())


class WorkspaceRuntime:
    """Runtime for executing pipelines across shops.

    The workspace runtime orchestrates pipeline execution by:
    - Managing shop runtimes
    - Resolving cross-shop technique references
    - Maintaining shared context across pipeline steps
    - Handling pipeline configuration and timeouts

    Attributes:
        workspace: Workspace configuration
        providers: Provider registry
        shops: Dictionary of shop runtimes
    """

    def __init__(
        self,
        workspace: WorkspaceSettings,
        providers: ProviderRegistry,
    ) -> None:
        """Initialize workspace runtime.

        Args:
            workspace: Workspace configuration
            providers: Provider registry
        """
        self.workspace = workspace
        self.providers = providers
        self.shops = self._build_shops()
        self.budget_tracker: BudgetTracker | None = None
        self.template_engine = PipelineTemplateEngine()
        self.condition_evaluator = ConditionEvaluator()

        logger.info(
            "Initialized WorkspaceRuntime '%s' with %d shops and %d pipelines",
            workspace.name,
            len(self.shops),
            len(workspace.pipelines),
        )

    def _build_shops(self) -> dict[str, ShopRuntime]:
        """Build shop runtimes from workspace configuration.

        Returns:
            Dictionary mapping shop names to shop runtimes
        """
        shops = {}

        for shop_name, shop_config in self.workspace.shops.items():
            shops[shop_name] = ShopRuntime(
                name=shop_name,
                shop_cfg=shop_config,
                providers=self.providers,
            )
            logger.debug("Built shop runtime: %s", shop_name)

        return shops

    def _parse_step_reference(self, step_ref: str) -> tuple[str, str]:
        """Parse a step reference into shop and technique names.

        Format: "shop.technique" (e.g., "rag.chunker")

        Args:
            step_ref: Step reference string

        Returns:
            Tuple of (shop_name, technique_name)

        Raises:
            ValueError: If reference format is invalid
        """
        if "." not in step_ref:
            msg = f"Invalid step reference '{step_ref}': must be in format " "'shop.technique'"
            raise ValueError(msg)

        shop_name, technique_name = step_ref.split(".", 1)
        return shop_name, technique_name

    def _resolve_params(
        self,
        params: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Resolve template strings in parameters recursively.

        Processes nested dicts and lists, rendering any strings with {{ }} or {% %} syntax.

        Args:
            params: Raw parameters (may contain templates)
            context: Execution context (input, context, env)

        Returns:
            Resolved parameters with templates rendered
        """
        resolved = {}

        for key, value in params.items():
            if isinstance(value, str):
                # Check if contains template syntax
                if self.template_engine.has_template_syntax(value):
                    resolved[key] = self.template_engine.render(value, context)
                else:
                    resolved[key] = value

            elif isinstance(value, dict):
                # Recurse for nested dicts
                resolved[key] = self._resolve_params(value, context)

            elif isinstance(value, list):
                # Recurse for lists
                resolved_list = []
                for item in value:
                    if isinstance(item, dict):
                        resolved_list.append(self._resolve_params(item, context))
                    elif isinstance(item, str):
                        if self.template_engine.has_template_syntax(item):
                            resolved_list.append(self.template_engine.render(item, context))
                        else:
                            resolved_list.append(item)
                    else:
                        resolved_list.append(item)
                resolved[key] = resolved_list

            else:
                # Pass through non-template values
                resolved[key] = value

        return resolved

    def _evaluate_step_condition(
        self,
        condition: str,
        context: dict[str, Any],
        step_name: str,
    ) -> bool:
        """Evaluate a step condition using unified condition evaluator.

        This provides consistent condition evaluation across all step types
        (technique steps, MCP steps, and control flow constructs).

        Args:
            condition: Condition expression to evaluate
            context: Execution context
            step_name: Name of step for logging

        Returns:
            True if condition is met, False otherwise

        Raises:
            PipelineExecutionError: If condition evaluation fails
        """
        try:
            return self.condition_evaluator.evaluate(condition, context)
        except ConditionEvaluationError as e:
            msg = f"Failed to evaluate condition for step '{step_name}': {e}"
            raise PipelineExecutionError(msg) from e

    async def _execute_mcp_step(
        self,
        step: PipelineStepConfig,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute an MCP tool step.

        Args:
            step: MCP step configuration
            context: Shared context dictionary

        Returns:
            Result from MCP tool execution

        Raises:
            PipelineExecutionError: If MCP provider not found or tool execution fails
        """
        from sibyl.runtime.providers.mcp_adapters import create_mcp_tool_step

        # Get MCP provider
        provider_name = step.provider
        if provider_name not in self.workspace.providers.mcp:
            available = ", ".join(self.workspace.providers.mcp.keys())
            msg = f"MCP provider '{provider_name}' not found. Available providers: {available}"
            raise PipelineExecutionError(msg)

        mcp_config = self.workspace.providers.mcp[provider_name]

        # Get provider instance from registry
        # Note: We need to instantiate the provider based on transport type
        if mcp_config.transport == "http":
            from sibyl.runtime.providers.mcp import HTTPMCPProvider

            provider = HTTPMCPProvider(
                endpoint=mcp_config.url,
                tools=mcp_config.tools,
                timeout_s=mcp_config.timeout_s,
                auth=mcp_config.auth,
            )
        elif mcp_config.transport == "stdio":
            from sibyl.runtime.providers.mcp import StdIOMCPProvider

            provider = StdIOMCPProvider(
                command=" ".join(mcp_config.command),
                tools=mcp_config.tools,
                timeout_s=mcp_config.timeout_s,
            )
        else:
            msg = f"Unsupported MCP transport type: {mcp_config.transport}"
            raise PipelineExecutionError(msg)

        # Create adapter for the tool
        tool_adapter = create_mcp_tool_step(provider, step.tool)

        # Prepare and resolve parameters
        raw_params = step.params or {}
        params = self._resolve_params(raw_params, context)

        # Execute the tool
        logger.info(
            "Executing MCP tool '%s' from provider '%s' with params: %s",
            step.tool,
            provider_name,
            params,
        )

        result = await tool_adapter(**params)

        logger.debug("MCP tool '%s' completed successfully", step.tool)

        return result

    async def _execute_loop(
        self,
        loop_config: LoopConfig,
        context: dict[str, Any],
        pipeline: PipelineConfig,
    ) -> None:
        """Execute a loop block (C1.1).

        Supports three loop modes:
        1. for_each: Iterate over a collection
        2. while: Loop while condition is true
        3. Both: for_each with additional while check

        Args:
            loop_config: Loop configuration
            context: Shared context dictionary (mutated in-place)
            pipeline: Pipeline configuration (for budget access)

        Raises:
            PipelineExecutionError: If loop execution fails
            ConditionEvaluationError: If condition evaluation fails
        """
        logger.info("Executing loop (max_iterations=%s)", loop_config.max_iterations)

        iteration = 0
        items = []

        # Evaluate for_each if provided
        if loop_config.for_each:
            # Render the for_each template to get collection
            for_each_value = self.template_engine.render(loop_config.for_each, context)

            # Ensure it's iterable
            if not hasattr(for_each_value, "__iter__") or isinstance(for_each_value, str):
                msg = (
                    f"for_each expression must evaluate to an iterable collection, "
                    f"got {type(for_each_value).__name__}"
                )
                raise PipelineExecutionError(msg)

            items = list(for_each_value)
            logger.debug("Loop will iterate over %s items", len(items))

        # Main loop
        while iteration < loop_config.max_iterations:
            iteration += 1

            # Set up loop context
            loop_context = dict(context)
            loop_context["loop"] = {
                "iteration": iteration,
                "max_iterations": loop_config.max_iterations,
            }

            # Handle for_each iteration
            if items:
                if iteration > len(items):
                    logger.debug("for_each exhausted, breaking loop")
                    break

                # Bind current item to variable
                current_item = items[iteration - 1]
                loop_context["loop"][loop_config.var] = current_item
                # Also expose at top level for convenience
                loop_context[loop_config.var] = current_item

                logger.debug(
                    "Loop iteration %s/%s: %s=%s",
                    iteration,
                    len(items),
                    loop_config.var,
                    current_item,
                )

            # Check while condition
            if loop_config.while_condition:
                try:
                    should_continue = self.condition_evaluator.evaluate(
                        loop_config.while_condition,
                        loop_context,
                    )

                    if not should_continue:
                        logger.info(
                            "Loop while condition false at iteration %s, breaking", iteration
                        )
                        break

                except ConditionEvaluationError as e:
                    msg = f"Failed to evaluate loop while condition: {e}"
                    raise PipelineExecutionError(msg) from e

            # Execute loop body steps
            for step in loop_config.steps:
                await self._execute_step(step, loop_context, pipeline)

            # Check break_on condition
            if loop_config.break_on:
                try:
                    should_break = self.condition_evaluator.evaluate(
                        loop_config.break_on,
                        loop_context,
                    )

                    if should_break:
                        logger.info("Loop break condition met at iteration %s, breaking", iteration)
                        break

                except ConditionEvaluationError as e:
                    msg = f"Failed to evaluate loop break condition: {e}"
                    raise PipelineExecutionError(msg) from e

            # Update main context with loop context changes
            # (preserve results accumulated during loop)
            context["context"].update(loop_context.get("context", {}))

            # For pure while loops without for_each, check if we need to continue
            if not items and not loop_config.while_condition:
                # Infinite loop without condition - rely on max_iterations
                pass

        logger.info("Loop completed after %s iterations", iteration)

    async def _execute_parallel(
        self,
        parallel_config: ParallelConfig,
        context: dict[str, Any],
        pipeline: PipelineConfig,
    ) -> None:
        """Execute steps in parallel (C1.2).

        Runs steps concurrently and collects results into a dict.

        Args:
            parallel_config: Parallel execution configuration
            context: Shared context dictionary (mutated in-place)
            pipeline: Pipeline configuration (for budget access)

        Raises:
            PipelineExecutionError: If parallel execution fails
        """
        logger.info(
            "Executing %s steps in parallel (fail_fast=%s)",
            len(parallel_config.steps),
            parallel_config.fail_fast,
        )

        # Create tasks for each step
        tasks = []
        step_names = []

        for i, step in enumerate(parallel_config.steps):
            # Use step name if provided, otherwise generate
            step_name = step.name or f"step_{i}"
            step_names.append(step_name)

            # Create a copy of context for this task
            task_context = dict(context)
            task_context["context"] = dict(context.get("context", {}))

            # Create async task
            async def execute_parallel_step(
                s: PipelineStepConfig,
                ctx: dict[str, Any],
                name: str,
            ):
                """Execute a single step in parallel."""
                try:
                    logger.debug("Parallel step '%s' starting", name)
                    await self._execute_step(s, ctx, pipeline)
                    logger.debug("Parallel step '%s' completed", name)
                    return (name, ctx, None)
                except Exception as e:
                    logger.exception("Parallel step '%s' failed: %s", name, e)
                    return (name, ctx, e)

            task = execute_parallel_step(step, task_context, step_name)
            tasks.append(task)

        # Execute with optional timeout
        tasks_gathered = asyncio.gather(*tasks, return_exceptions=not parallel_config.fail_fast)

        try:
            if parallel_config.timeout_s:
                results = await asyncio.wait_for(
                    tasks_gathered,
                    timeout=parallel_config.timeout_s,
                )
            else:
                results = await tasks_gathered

        except asyncio.CancelledError:
            # Cancel all in-flight tasks on cancellation
            logger.warning("Parallel execution cancelled, cancelling in-flight tasks")
            tasks_gathered.cancel()
            msg = "Parallel execution was cancelled"
            raise PipelineExecutionError(msg, cancelled=True)
        except TimeoutError:
            # Cancel all in-flight tasks on timeout
            tasks_gathered.cancel()
            msg = f"Parallel execution timed out after {parallel_config.timeout_s}s"
            raise PipelineExecutionError(msg)

        # Process results
        parallel_results = {}
        errors = []
        failed_steps = []

        for result in results:
            if isinstance(result, Exception):
                errors.append(result)
                failed_steps.append(("unknown", result))
                if parallel_config.fail_fast:
                    raise result
            else:
                name, task_context, error = result
                if error:
                    errors.append(error)
                    failed_steps.append((name, error))
                    if parallel_config.fail_fast:
                        raise error
                else:
                    # Extract result from task context
                    parallel_results[name] = task_context.get("last_result")

        # Store results in context
        context[parallel_config.gather] = parallel_results
        context["context"][parallel_config.gather] = parallel_results

        if errors:
            # Log detailed information about failures when fail_fast=False
            logger.warning(
                "Parallel execution completed with %s error(s) (fail_fast=False, continuing)",
                len(errors),
            )
            for step_name, error in failed_steps:
                error_type = type(error).__name__
                error_msg = str(error)
                # Truncate very long error messages
                if len(error_msg) > 200:
                    error_msg = error_msg[:200] + "..."
                logger.error("  Failed step '%s': %s: %s", step_name, error_type, error_msg)
        else:
            logger.info("Parallel execution completed successfully")

    async def _execute_try_catch_finally(
        self,
        try_config: TryConfig,
        context: dict[str, Any],
        pipeline: PipelineConfig,
    ) -> None:
        """Execute try/catch/finally block (C1.3).

        Args:
            try_config: Try/catch/finally configuration
            context: Shared context dictionary (mutated in-place)
            pipeline: Pipeline configuration (for budget access)

        Raises:
            Exception: If no catch block matches or finally raises
        """
        logger.info("Executing try/catch/finally block")

        error_caught = None
        error_handled = False

        # Execute try block
        try:
            logger.debug("Executing try block")
            for step in try_config.steps:
                await self._execute_step(step, context, pipeline)
            logger.debug("Try block completed successfully")

        except Exception as e:
            error_caught = e
            logger.info("Try block raised error: %s: %s", type(e).__name__, e)

            # Unwrap PipelineExecutionError to get original error type
            # This allows catch blocks to match on the actual error type (e.g., RuntimeError)
            # rather than the wrapper (PipelineExecutionError)
            original_error = e.__cause__ if hasattr(e, "__cause__") and e.__cause__ else e
            error_type = type(original_error).__name__

            # Build error context for catch blocks
            error_context = dict(context)
            error_context["error"] = {
                "type": error_type,
                "message": str(original_error),
                "details": getattr(original_error, "details", {}),
            }

            # Try catch blocks in order
            if try_config.catch:
                for i, catch_block in enumerate(try_config.catch):
                    try:
                        # Evaluate when condition
                        should_handle = self.condition_evaluator.evaluate(
                            catch_block.when,
                            error_context,
                        )

                        if should_handle:
                            logger.info(
                                "Error matched catch block %s (condition: %s)",
                                i + 1,
                                catch_block.when,
                            )

                            # Execute catch steps
                            for step in catch_block.steps:
                                await self._execute_step(step, error_context, pipeline)

                            # Update main context with catch results
                            context["context"].update(error_context.get("context", {}))

                            error_handled = True
                            logger.debug("Catch block completed successfully")
                            break

                    except ConditionEvaluationError as cond_error:
                        logger.warning(
                            "Failed to evaluate catch condition %s: %s", i + 1, cond_error
                        )
                        continue
                    except Exception as catch_error:
                        logger.exception("Catch block %s raised error: %s", i + 1, catch_error)
                        # Catch block errors replace original error
                        error_caught = catch_error
                        break

            if not error_handled:
                logger.warning("No catch block matched, error will be re-raised")

        finally:
            # Always execute finally block
            if try_config.finally_steps:
                logger.debug("Executing finally block")
                try:
                    for step in try_config.finally_steps:
                        await self._execute_step(step, context, pipeline)
                    logger.debug("Finally block completed successfully")
                except Exception as finally_error:
                    logger.exception("Finally block raised error: %s", finally_error)
                    # Finally errors take precedence
                    if error_caught:
                        logger.exception(
                            "Original error suppressed by finally error: %s", error_caught
                        )
                    raise

        # Re-raise original error if not handled
        if error_caught and not error_handled:
            raise error_caught

    async def _execute_step(
        self,
        step: PipelineStepConfig,
        context: dict[str, Any],
        pipeline: PipelineConfig,
    ) -> None:
        """Execute a single pipeline step.

        Supports five step types:
        1. Technique steps (use=...)
        2. MCP tool steps (shop=mcp, provider=..., tool=...)
        3. Loop steps (loop={...})
        4. Parallel steps (parallel={...})
        5. Try/catch/finally steps (try_block={...})

        Args:
            step: Step configuration
            context: Shared context dictionary (mutated in-place)
            pipeline: Pipeline configuration (for budget access)

        Raises:
            PipelineExecutionError: If step execution fails
            BudgetExceededError: If budget limits exceeded
            StepTimeoutError: If step timeout exceeded
        """
        try:
            # Handle control flow steps (C1.1, C1.2, C1.3)
            if step.loop:
                await self._execute_loop(step.loop, context, pipeline)
                return

            if step.parallel:
                await self._execute_parallel(step.parallel, context, pipeline)
                return

            if step.try_block:
                await self._execute_try_catch_finally(step.try_block, context, pipeline)
                return

            # Check if this is an MCP step
            is_mcp_step = step.shop == "mcp"

            if is_mcp_step:
                # Handle MCP tool step
                step_name = f"mcp.{step.provider}.{step.tool}"

                # Check condition if present (unified with technique steps)
                if step.condition:
                    should_execute = self._evaluate_step_condition(
                        step.condition, context, step_name
                    )
                    if not should_execute:
                        logger.info(
                            "Skipping MCP step '%s' - condition '%s' not met",
                            step_name,
                            step.condition,
                        )
                        return

                # Reset step-level budget counters
                if self.budget_tracker:
                    self.budget_tracker.reset_step()

                # Check budgets before execution
                if self.budget_tracker:
                    if step.budget:
                        self.budget_tracker.check_budget(
                            step.budget, scope=f"step:{step_name}", use_step_totals=False
                        )
                    if pipeline.budget:
                        self.budget_tracker.check_budget(
                            pipeline.budget, scope="pipeline", use_step_totals=False
                        )
                    if self.workspace.budget:
                        self.budget_tracker.check_budget(
                            self.workspace.budget, scope="global", use_step_totals=False
                        )

                # Execute MCP tool with optional timeout
                async def execute_mcp_tool() -> Any:
                    return await self._execute_mcp_step(step, context)

                if step.timeout_s:
                    try:
                        result = await asyncio.wait_for(
                            execute_mcp_tool(),
                            timeout=step.timeout_s,
                        )
                    except TimeoutError:
                        raise StepTimeoutError(
                            step_name=step_name,
                            timeout_s=step.timeout_s,
                        )
                else:
                    result = await execute_mcp_tool()

                # Update context with result
                # Store in both top-level  and nested context namespace (templates)
                context[f"{step.tool}_result"] = result
                context["last_result"] = result
                context["context"][f"{step.tool}_result"] = result
                context["context"]["last_result"] = result

                # Check budgets after execution
                if self.budget_tracker:
                    if step.budget:
                        self.budget_tracker.check_budget(
                            step.budget, scope=f"step:{step_name}", use_step_totals=True
                        )
                    if pipeline.budget:
                        self.budget_tracker.check_budget(
                            pipeline.budget, scope="pipeline", use_step_totals=False
                        )
                    if self.workspace.budget:
                        self.budget_tracker.check_budget(
                            self.workspace.budget, scope="global", use_step_totals=False
                        )

                logger.debug("MCP step '%s' completed, context updated", step_name)
                return

            # Parse step reference for technique steps
            shop_name, technique_name = self._parse_step_reference(step.use)

            # Check condition if present (unified with MCP steps)
            if step.condition:
                should_execute = self._evaluate_step_condition(step.condition, context, step.use)
                if not should_execute:
                    logger.info(
                        "Skipping step '%s' - condition '%s' not met", step.use, step.condition
                    )
                    return

            # Reset step-level budget counters
            if self.budget_tracker:
                self.budget_tracker.reset_step()

            # Check budgets before execution (hierarchy: step -> pipeline -> global)
            if self.budget_tracker:
                # Check step budget
                if step.budget:
                    self.budget_tracker.check_budget(
                        step.budget, scope=f"step:{step.use}", use_step_totals=False
                    )
                # Check pipeline budget
                if pipeline.budget:
                    self.budget_tracker.check_budget(
                        pipeline.budget, scope="pipeline", use_step_totals=False
                    )
                # Check global budget
                if self.workspace.budget:
                    self.budget_tracker.check_budget(
                        self.workspace.budget, scope="global", use_step_totals=False
                    )

            # Get shop runtime
            if shop_name not in self.shops:
                available = ", ".join(self.shops.keys())
                msg = f"Shop '{shop_name}' not found. Available shops: {available}"
                raise PipelineExecutionError(msg)

            shop = self.shops[shop_name]

            # Execute technique with optional timeout
            step_config = step.config or {}

            async def execute_technique() -> Any:
                return await shop.run_technique(
                    logical_name=technique_name,
                    context=context,
                    config=step_config,
                )

            if step.timeout_s:
                # Execute with step timeout
                try:
                    result = await asyncio.wait_for(
                        execute_technique(),
                        timeout=step.timeout_s,
                    )
                except TimeoutError:
                    raise StepTimeoutError(
                        step_name=step.use,
                        timeout_s=step.timeout_s,
                    )
            else:
                # Execute without step timeout
                result = await execute_technique()

            # Update context with result
            # Store in both top-level  and nested context namespace (templates)
            context[f"{technique_name}_result"] = result.get("result")
            context["last_result"] = result.get("result")
            context["context"][f"{technique_name}_result"] = result.get("result")
            context["context"]["last_result"] = result.get("result")

            # Check budgets after execution
            if self.budget_tracker:
                # Check step budget
                if step.budget:
                    self.budget_tracker.check_budget(
                        step.budget, scope=f"step:{step.use}", use_step_totals=True
                    )
                # Check pipeline budget
                if pipeline.budget:
                    self.budget_tracker.check_budget(
                        pipeline.budget, scope="pipeline", use_step_totals=False
                    )
                # Check global budget
                if self.workspace.budget:
                    self.budget_tracker.check_budget(
                        self.workspace.budget, scope="global", use_step_totals=False
                    )

            logger.debug("Step '%s' completed, context updated", step.use)

        except asyncio.CancelledError:
            # Handle cancellation explicitly
            step_name = (
                step.use
                if hasattr(step, "use") and step.use
                else f"mcp.{step.provider}.{step.tool}"
            )
            logger.warning("Step '%s' was cancelled", step_name)
            msg = f"Pipeline step '{step_name}' was cancelled"
            raise PipelineExecutionError(msg, cancelled=True)
        except (BudgetExceededError, StepTimeoutError):
            # Re-raise budget and timeout errors as-is
            raise
        except Exception as e:
            step_name = (
                step.use
                if hasattr(step, "use") and step.use
                else f"mcp.{step.provider}.{step.tool}"
            )
            logger.exception("Step '%s' failed: %s", step_name, e)
            msg = f"Pipeline step '{step_name}' failed: {e}"
            raise PipelineExecutionError(msg) from e

    async def run_pipeline(
        self,
        pipeline_name: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a named pipeline.

        Args:
            pipeline_name: Pipeline name from workspace configuration
            **kwargs: Input parameters for pipeline execution

        Returns:
            Dictionary with pipeline execution results, including:
            - All context values accumulated during execution
            - Special key 'success' indicating completion status
            - Budget tracking info (if budgets configured)

        Raises:
            PipelineExecutionError: If pipeline not found or execution fails
            BudgetExceededError: If budget limits exceeded
        """
        # Get pipeline configuration
        if pipeline_name not in self.workspace.pipelines:
            available = ", ".join(self.workspace.pipelines.keys())
            msg = f"Pipeline '{pipeline_name}' not found. " f"Available pipelines: {available}"
            raise PipelineExecutionError(msg)

        pipeline = self.workspace.pipelines[pipeline_name]

        logger.info("Starting pipeline '%s' with %s steps", pipeline_name, len(pipeline.steps))

        # Initialize budget tracker if any budgets are configured
        if self.workspace.budget or pipeline.budget or any(step.budget for step in pipeline.steps):
            self.budget_tracker = BudgetTracker()
            logger.debug("Budget tracking enabled for pipeline execution")

        # Initialize context with input parameters
        # Note: We provide both "input" namespace (for templates) and top-level kwargs
        context: dict[str, Any] = {
            "pipeline_name": pipeline_name,
            "pipeline_shop": pipeline.shop,
            "input": kwargs,  # Template-friendly namespace
            "context": {},  # Step outputs will be stored here
            **kwargs,  # Backward compatibility
        }

        # Create timeout if specified
        timeout = pipeline.timeout_s

        try:
            if timeout:
                # Execute with timeout
                await asyncio.wait_for(
                    self._execute_pipeline_steps(pipeline, context),
                    timeout=timeout,
                )
            else:
                # Execute without timeout
                await self._execute_pipeline_steps(pipeline, context)

            logger.info("Pipeline '%s' completed successfully", pipeline_name)

            # Mark as successful
            context["success"] = True

            # Include budget usage in context
            if self.budget_tracker:
                context["budget_usage"] = {
                    "total_cost_usd": self.budget_tracker.total_cost_usd,
                    "total_tokens": self.budget_tracker.total_tokens,
                    "total_requests": self.budget_tracker.total_requests,
                }

            return context

        except asyncio.CancelledError:
            logger.warning("Pipeline '%s' was cancelled", pipeline_name)
            context["success"] = False
            context["error"] = "Pipeline execution was cancelled"
            msg = f"Pipeline '{pipeline_name}' was cancelled"
            raise PipelineExecutionError(msg, cancelled=True)
        except TimeoutError:
            logger.exception("Pipeline '%s' timed out after %ss", pipeline_name, timeout)
            msg = f"Pipeline '{pipeline_name}' timed out after {timeout}s"
            raise PipelineExecutionError(msg)
        except (BudgetExceededError, StepTimeoutError):
            # Re-raise budget and timeout errors as-is
            raise
        except Exception as e:
            logger.exception("Pipeline '%s' failed: %s", pipeline_name, e)
            context["success"] = False
            context["error"] = str(e)
            msg = f"Pipeline '{pipeline_name}' execution failed: {e}"
            raise PipelineExecutionError(msg) from e
        finally:
            # Clean up budget tracker
            self.budget_tracker = None

    async def _execute_pipeline_steps(
        self,
        pipeline: PipelineConfig,
        context: dict[str, Any],
    ) -> None:
        """Execute all steps in a pipeline sequentially.

        Args:
            pipeline: Pipeline configuration
            context: Shared context dictionary (mutated in-place)
        """
        for i, step in enumerate(pipeline.steps, 1):
            logger.debug("Executing step %s/%s: %s", i, len(pipeline.steps), step.use)
            await self._execute_step(step, context, pipeline)

    def list_pipelines(self) -> list[str]:
        """List all available pipeline names.

        Returns:
            List of pipeline names
        """
        return list(self.workspace.pipelines.keys())

    def get_pipeline_info(self, pipeline_name: str) -> dict[str, Any] | None:
        """Get information about a pipeline.

        Args:
            pipeline_name: Pipeline name

        Returns:
            Dictionary with pipeline metadata or None if not found
        """
        if pipeline_name not in self.workspace.pipelines:
            return None

        pipeline = self.workspace.pipelines[pipeline_name]

        return {
            "name": pipeline_name,
            "shop": pipeline.shop,
            "description": pipeline.description,
            "entrypoint": pipeline.entrypoint,
            "num_steps": len(pipeline.steps),
            "timeout_s": pipeline.timeout_s,
            "steps": [step.use for step in pipeline.steps],
        }

    async def run_pipeline_v2(
        self,
        pipeline_name: str,
        **kwargs: Any,
    ) -> "PipelineResult":
        """Execute a named pipeline with PipelineResult envelope (v2 API).

        This is the new v2 API that returns a structured PipelineResult envelope
        with observability metadata, error handling, and timing information.

        Args:
            pipeline_name: Pipeline name from workspace configuration
            **kwargs: Input parameters for pipeline execution

        Returns:
            PipelineResult with success/error status and observability data

        Example:
            result = await runtime.run_pipeline_v2("web_research", query="AI")
            if result.ok:
                print(f"Success: {result.data}")
            else:
                print(f"Error: {result.error.message}")
        """
        import time
        import uuid
        from datetime import datetime

        from sibyl.runtime.pipeline.result import PipelineError, PipelineResult

        # Generate trace ID for observability
        trace_id = str(uuid.uuid4())
        start_time = datetime.utcnow().isoformat() + "Z"
        start_ms = time.time() * 1000

        logger.info(
            "Starting pipeline '%s' [trace_id=%s]",
            pipeline_name,
            trace_id,
            extra={"trace_id": trace_id, "pipeline_name": pipeline_name},
        )

        try:
            # Execute pipeline using existing run_pipeline method
            context = await self.run_pipeline(pipeline_name, **kwargs)

            end_ms = time.time() * 1000
            duration_ms = end_ms - start_ms
            end_time = datetime.utcnow().isoformat() + "Z"

            # Check if pipeline succeeded
            if context.get("success", True):
                logger.info(
                    "Pipeline '%s' completed successfully [trace_id=%s, duration=%.2fms]",
                    pipeline_name,
                    trace_id,
                    duration_ms,
                    extra={
                        "trace_id": trace_id,
                        "pipeline_name": pipeline_name,
                        "duration_ms": duration_ms,
                    },
                )

                return PipelineResult.success(
                    data=context,
                    trace_id=trace_id,
                    duration_ms=duration_ms,
                    pipeline_name=pipeline_name,
                    start_time=start_time,
                    end_time=end_time,
                )
            # Pipeline returned failure status
            error_msg = context.get("error", "Pipeline execution failed")
            logger.error(
                "Pipeline '%s' failed: %s [trace_id=%s, duration=%.2fms]",
                pipeline_name,
                error_msg,
                trace_id,
                duration_ms,
                extra={
                    "trace_id": trace_id,
                    "pipeline_name": pipeline_name,
                    "duration_ms": duration_ms,
                },
            )

            return PipelineResult.error(
                error=PipelineError(
                    type="PipelineExecutionError", message=error_msg, details={"context": context}
                ),
                trace_id=trace_id,
                duration_ms=duration_ms,
                pipeline_name=pipeline_name,
                start_time=start_time,
                end_time=end_time,
            )

        except BudgetExceededError as e:
            end_ms = time.time() * 1000
            duration_ms = end_ms - start_ms
            end_time = datetime.utcnow().isoformat() + "Z"

            logger.exception(
                "Pipeline '%s' budget exceeded: %s [trace_id=%s]",
                pipeline_name,
                e.message,
                trace_id,
                extra={"trace_id": trace_id, "pipeline_name": pipeline_name},
            )

            return PipelineResult.error(
                error=PipelineError(
                    type="BudgetExceededError", message=e.message, details=e.details
                ),
                trace_id=trace_id,
                duration_ms=duration_ms,
                pipeline_name=pipeline_name,
                start_time=start_time,
                end_time=end_time,
            )

        except StepTimeoutError as e:
            end_ms = time.time() * 1000
            duration_ms = end_ms - start_ms
            end_time = datetime.utcnow().isoformat() + "Z"

            logger.exception(
                "Pipeline '%s' step timeout: %s [trace_id=%s]",
                pipeline_name,
                e.message,
                trace_id,
                extra={"trace_id": trace_id, "pipeline_name": pipeline_name},
            )

            return PipelineResult.error(
                error=PipelineError(type="StepTimeoutError", message=e.message, details=e.details),
                trace_id=trace_id,
                duration_ms=duration_ms,
                pipeline_name=pipeline_name,
                start_time=start_time,
                end_time=end_time,
            )

        except PipelineExecutionError as e:
            end_ms = time.time() * 1000
            duration_ms = end_ms - start_ms
            end_time = datetime.utcnow().isoformat() + "Z"

            logger.exception(
                "Pipeline '%s' execution error: %s [trace_id=%s]",
                pipeline_name,
                e,
                trace_id,
                extra={"trace_id": trace_id, "pipeline_name": pipeline_name},
            )

            return PipelineResult.error(
                error=PipelineError.from_exception(e, error_type="PipelineExecutionError"),
                trace_id=trace_id,
                duration_ms=duration_ms,
                pipeline_name=pipeline_name,
                start_time=start_time,
                end_time=end_time,
            )

        except Exception as e:
            end_ms = time.time() * 1000
            duration_ms = end_ms - start_ms
            end_time = datetime.utcnow().isoformat() + "Z"

            logger.exception(
                "Pipeline '%s' unexpected error: %s [trace_id=%s]",
                pipeline_name,
                e,
                trace_id,
                extra={"trace_id": trace_id, "pipeline_name": pipeline_name},
            )

            return PipelineResult.error(
                error=PipelineError.from_exception(e),
                trace_id=trace_id,
                duration_ms=duration_ms,
                pipeline_name=pipeline_name,
                start_time=start_time,
                end_time=end_time,
            )

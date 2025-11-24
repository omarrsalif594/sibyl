"""Response generation strategies."""

import logging
from importlib import import_module
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.config_cascade import ConfigCascade
from sibyl.techniques.observability import execute_with_observability
from sibyl.techniques.protocols import BaseSubtechnique, BaseTechnique

logger = logging.getLogger(__name__)


class GenerationTechnique(BaseTechnique):
    """Response generation orchestrator."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._name = "generation"
        self._description = "Response generation strategies"
        self._config_path = config_path or Path(__file__).parent / "config.yaml"
        self._technique_config = self.load_config(self._config_path)
        self._subtechniques: dict[str, dict[str, BaseSubtechnique]] = {}
        self._subtech_configs: dict[str, dict[str, Any]] = {}
        self._discover_subtechniques()

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def subtechniques(self) -> dict[str, dict[str, BaseSubtechnique]]:
        return self._subtechniques

    def register_subtechnique(
        self,
        subtechnique: BaseSubtechnique,
        subtechnique_name: str,
        implementation: str | None = None,
    ) -> None:
        impl_name = implementation or subtechnique.name
        self._subtechniques.setdefault(subtechnique_name, {})[impl_name] = subtechnique
        logger.debug("Registered generation subtechnique %s:%s", subtechnique_name, impl_name)

    def execute(
        self,
        input_data: Any,
        subtechnique: str,
        implementation: str = "default",
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        if subtechnique not in self._subtechniques:
            msg = (
                f"Unknown subtechnique '{subtechnique}'. "
                f"Available: {list(self._subtechniques.keys())}"
            )
            raise ValueError(msg)

        impl_name = implementation
        if implementation == "default":
            impl_name = self._subtech_configs.get(subtechnique, {}).get("default_implementation")
        if not impl_name:
            impl_name = next(iter(self._subtechniques[subtechnique].keys()))

        if impl_name not in self._subtechniques[subtechnique]:
            msg = (
                f"Unknown implementation '{impl_name}' for '{subtechnique}'. "
                f"Available: {list(self._subtechniques[subtechnique].keys())}"
            )
            raise ValueError(msg)

        impl = self._subtechniques[subtechnique][impl_name]
        subtech_config = impl.get_config() or {}
        if config:
            subtech_config = {**subtech_config, **config}

        cascade = ConfigCascade(
            global_config=kwargs.get("global_config", {}),
            technique_config=self._technique_config,
            subtechnique_config=subtech_config,
        )
        merged_config = cascade.merge()

        if not impl.validate_config(merged_config):
            msg = f"Invalid configuration for {subtechnique}:{impl_name}"
            raise ValueError(msg)

        return execute_with_observability(
            technique_name=self.name,
            subtechnique=subtechnique,
            implementation=impl_name,
            input_data=input_data,
            config=merged_config,
            executor=lambda: impl.execute(input_data, merged_config),
        )

    def get_config(self) -> dict[str, Any]:
        return self._technique_config.copy()

    def load_config(self, config_path: Path) -> dict[str, Any]:
        if not config_path.exists():
            logger.warning("Config file not found for generation: %s", config_path)
            return {}
        try:
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            msg = f"Invalid YAML in {config_path}: {exc}"
            raise ValueError(msg) from None

    def list_subtechniques(self) -> dict[str, list[str]]:
        return {name: list(impls.keys()) for name, impls in self._subtechniques.items()}

    def _discover_subtechniques(self) -> None:
        base = "sibyl.techniques.ai_generation.generation.subtechniques"
        mapping = {
            "basic_generation": [
                (f"{base}.basic_generation.default.prompt_based", "PromptBasedImplementation"),
                (f"{base}.basic_generation.default.template", "TemplateImplementation"),
            ],
            "chain_of_thought": [
                (f"{base}.chain_of_thought.default.step_by_step", "StepByStepImplementation"),
                (f"{base}.chain_of_thought.default.reasoning", "ReasoningImplementation"),
            ],
            "self_consistency": [
                (f"{base}.self_consistency.default.voting", "VotingImplementation"),
                (f"{base}.self_consistency.default.multi_path", "MultiPathImplementation"),
            ],
            "tree_of_thought": [
                (f"{base}.tree_of_thought.default.tot_exploration", "TotExplorationImplementation"),
            ],
            "react": [
                (f"{base}.react.default.react_pattern", "ReactPatternImplementation"),
                (f"{base}.react.default.tool_use", "ToolUseImplementation"),
            ],
        }

        for subtechnique, implementations in mapping.items():
            self._subtech_configs[subtechnique] = self._load_subtech_config(subtechnique)
            for module_path, class_name in implementations:
                self._load_and_register(subtechnique, module_path, class_name)

    def _load_and_register(self, subtechnique: str, module_path: str, class_name: str) -> None:
        try:
            module = import_module(module_path)
            impl_cls = getattr(module, class_name)
            instance = impl_cls()
            self.register_subtechnique(instance, subtechnique, instance.name)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "Failed to register generation implementation %s.%s: %s",
                module_path,
                class_name,
                exc,
            )

    def _load_subtech_config(self, subtechnique: str) -> dict[str, Any]:
        config_path = Path(__file__).parent / "subtechniques" / subtechnique / "config.yaml"
        if not config_path.exists():
            return {}
        try:
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            logger.warning("Invalid YAML for subtechnique %s: %s", subtechnique, exc)
            return {}

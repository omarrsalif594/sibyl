"""Ranking technique implementation."""

import logging
from pathlib import Path
from typing import Any

import yaml

from sibyl.techniques.protocols import BaseSubtechnique, BaseTechnique

logger = logging.getLogger(__name__)


class RankingTechnique(BaseTechnique):
    """Ranking orchestrator."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._name = "ranking"
        self._description = "Ranking technique"
        self._config_path = config_path or Path(__file__).parent / "config.yaml"
        self._technique_config = self.load_config(self._config_path)
        self._subtechniques: dict[str, dict[str, BaseSubtechnique]] = {}

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
        """Register a subtechnique implementation."""
        impl_name = implementation or subtechnique.name
        self._subtechniques.setdefault(subtechnique_name, {})[impl_name] = subtechnique
        logger.debug("Registered ranking subtechnique %s:%s", subtechnique_name, impl_name)

    def execute(
        self,
        input_data: Any,
        subtechnique: str,
        implementation: str = "default",
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute a ranking subtechnique."""
        if subtechnique not in self._subtechniques:
            msg = (
                f"Unknown subtechnique '{subtechnique}'. "
                f"Available: {list(self._subtechniques.keys())}"
            )
            raise ValueError(msg)

        impl_name = (
            implementation
            if implementation != "default"
            else next(iter(self._subtechniques[subtechnique].keys()))
        )

        if impl_name not in self._subtechniques[subtechnique]:
            msg = (
                f"Unknown implementation '{impl_name}' for '{subtechnique}'. "
                f"Available: {list(self._subtechniques[subtechnique].keys())}"
            )
            raise ValueError(msg)

        impl = self._subtechniques[subtechnique][impl_name]
        merged_config = {**self._technique_config, **(config or {})}

        return impl.execute(input_data, merged_config)

    def get_config(self) -> dict[str, Any]:
        return self._technique_config.copy()

    def load_config(self, config_path: Path) -> dict[str, Any]:
        if not config_path.exists():
            logger.warning("Config file not found for ranking: %s", config_path)
            return {}
        try:
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            msg = f"Invalid YAML in {config_path}: {exc}"
            raise ValueError(msg) from None

    def list_subtechniques(self) -> dict[str, list[str]]:
        """Return mapping of subtechnique categories to implementations."""
        return {name: list(impls.keys()) for name, impls in self._subtechniques.items()}


def build_technique(config_path: Path | None = None) -> RankingTechnique:
    """Build and return a ranking technique instance."""
    return RankingTechnique(config_path=config_path)

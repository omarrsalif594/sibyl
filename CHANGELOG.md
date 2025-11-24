# Changelog

## [0.1.0] - 2025-11-24

### Added
- Initial Sibyl core packages:
  - `sibyl.core` for contracts, protocols, artifact types, and error taxonomy
  - `sibyl.runtime` for workspace runtime, pipeline execution, and control flow
  - `sibyl.techniques` as a structured technique library (RAG, data integration, AI generation, orchestration, etc.)

- Configuration model:
  - Workspace and pipeline YAML configs
  - Technique registry and subtechnique templates
  - Routing profiles and plugin-compatible configuration structure

- Plugin and integration layer:
  - `plugins/common/sibyl_runner` as a shared execution helper for external frontends
  - Opencode adapter for mapping editor commands to Sibyl pipelines
  - OpenAI-style tools gateway to expose pipelines as tools/functions
  - Claude router facade with config-based routing (including `local_specialist` hooks, no automatic policy yet)
  - Custom plugin template for downstream integrations

- Training toolkit scaffolding:
  - `specialists/training_toolkit` synthetic-data-only training pipeline
  - Example configs for small models and Apple Silicon–friendly settings
  - Mock-friendly design with no real data or hard dependency on Unsloth

- Examples, tests, and guardrails:
  - `examples/` companies and shared infrastructure as a realistic testbed
  - Tests for plugins, runtime, architecture, and examples
  - Guardrail markers and benchmarking harness for CI

- Documentation and metadata:
  - Project overview and basic usage in `README`
  - `RELEASE_CHECKLIST`, testing conventions, and plugin docs
  - Apache 2.0 `LICENSE`
  - CI workflows for examples, guardrails, and benchmarks

### Status
- First public pre-1.0 release
- APIs and structures are expected to change between minor versions
- No stability guarantees yet; feedback and issues are welcome

"""
Generate tool catalog and documentation.

This script:
1. Bootstraps all tools (imports all tool modules)
2. Generates machine-readable JSON catalog
3. Generates human-readable Markdown documentation
4. Can be used in CI to detect catalog drift

Usage:
    python -m scripts.generate_tool_catalog
    python -m scripts.generate_tool_catalog --verify  # CI mode (fails if drift detected)
"""

import argparse
import json

# Add parent to path for imports
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sibyl.core.framework.tools.bootstrap import bootstrap_all_tools
from sibyl.core.framework.tools.tool_registry import get_registry


def generate_json_catalog(output_path: Path) -> None:
    """
    Generate machine-readable JSON catalog.

    Args:
        output_path: Path to write catalog.json
    """
    registry = get_registry()

    catalog = {
        "version": "1.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "stats": registry.get_stats(),
        "tools": [
            {
                "name": meta.name,
                "version": meta.version,
                "category": meta.category,
                "description": meta.description,
                "input_schema": meta.input_schema,
                "output_schema": meta.output_schema,
                "max_execution_time_ms": meta.max_execution_time_ms,
                "examples": meta.examples,
                "tags": meta.tags,
            }
            for meta in registry.list_tools()
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(catalog, indent=2))


def generate_markdown_docs(catalog_path: Path, output_path: Path) -> None:
    """
    Generate human-readable Markdown documentation.

    Args:
        catalog_path: Path to read catalog.json
        output_path: Path to write TOOL_CATALOG.md
    """
    catalog = json.loads(catalog_path.read_text())

    md = []
    md.append("# MCP Tools Catalog\n\n")
    md.append(f"**Generated:** {catalog.get('generated_at')}\n\n")
    md.append(f"**Version:** {catalog.get('version')}\n\n")

    # Stats
    stats = catalog.get("stats", {})
    md.append("## Statistics\n\n")
    md.append(f"- **Total Tools:** {stats.get('total_tools', 0)}\n")
    md.append(f"- **Unique Tools:** {stats.get('unique_tools', 0)}\n")
    md.append(f"- **Categories:** {', '.join(stats.get('categories', []))}\n\n")

    # Tools by category
    md.append("### Tools by Category\n\n")
    for category, count in stats.get("tools_by_category", {}).items():
        md.append(f"- **{category.title()}:** {count} tools\n")
    md.append("\n")

    # Group tools by category
    by_category = {}
    for tool in catalog["tools"]:
        cat = tool["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(tool)

    # Document each category
    for category in sorted(by_category.keys()):
        tools = by_category[category]
        md.append(f"## {category.title()} Tools\n\n")

        for tool in sorted(tools, key=lambda t: t["name"]):
            md.append(f"### `{tool['name']}` (v{tool['version']})\n\n")
            md.append(f"{tool['description']}\n\n")

            # Metadata
            md.append("**Metadata:**\n")
            md.append(f"- **Category:** {tool['category']}\n")
            md.append(f"- **Max Execution Time:** {tool['max_execution_time_ms']}ms\n")
            if tool.get("tags"):
                md.append(f"- **Tags:** {', '.join(tool['tags'])}\n")
            md.append("\n")

            # Input schema
            md.append("**Input Schema:**\n```json\n")
            md.append(json.dumps(tool["input_schema"], indent=2))
            md.append("\n```\n\n")

            # Output schema
            md.append("**Output Schema:**\n```json\n")
            md.append(json.dumps(tool["output_schema"], indent=2))
            md.append("\n```\n\n")

            # Examples
            if tool.get("examples"):
                md.append("**Examples:**\n\n")
                for i, ex in enumerate(tool["examples"], 1):
                    md.append(f"*Example {i}:*\n\n")
                    md.append("Input:\n```json\n")
                    md.append(json.dumps(ex.get("input", {}), indent=2))
                    md.append("\n```\n\n")
                    md.append("Output:\n```json\n")
                    md.append(json.dumps(ex.get("output", {}), indent=2))
                    md.append("\n```\n\n")

            md.append("---\n\n")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(md))


def verify_catalog(catalog_path: Path) -> bool:
    """
    Verify catalog against committed version (for CI).

    Args:
        catalog_path: Path to generated catalog

    Returns:
        True if catalog matches committed version, False otherwise
    """
    if not catalog_path.exists():
        return False

    # Regenerate catalog
    import tempfile  # noqa: PLC0415 - can be moved to top

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        # Bootstrap and generate fresh catalog
        bootstrap_all_tools()
        generate_json_catalog(tmp_path)

        # Load both catalogs
        committed = json.loads(catalog_path.read_text())
        generated = json.loads(tmp_path.read_text())

        # Compare tools (ignore generated_at timestamp)
        committed_tools = {t["name"]: t for t in committed.get("tools", [])}
        generated_tools = {t["name"]: t for t in generated.get("tools", [])}

        if committed_tools.keys() != generated_tools.keys():
            return False

        # Check for schema changes
        for tool_name in committed_tools:
            if committed_tools[tool_name] != generated_tools[tool_name]:
                return False

        return True

    finally:
        tmp_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate MCP tool catalog")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify catalog matches committed version (for CI)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent.parent / "data",
        help="Output directory for catalog",
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path(__file__).parent.parent / "docs" / "technical",
        help="Output directory for Markdown docs",
    )

    args = parser.parse_args()

    catalog_path = args.output_dir / "tool_catalog.json"
    docs_path = args.docs_dir / "TOOL_CATALOG.md"

    if args.verify:
        # CI mode: verify catalog is up to date
        success = verify_catalog(catalog_path)
        sys.exit(0 if success else 1)
    else:
        # Generation mode
        bootstrap_all_tools()

        generate_json_catalog(catalog_path)

        generate_markdown_docs(catalog_path, docs_path)


if __name__ == "__main__":
    main()

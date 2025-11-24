#!/usr/bin/env python3
"""
Circular Import and Layering Violation Detector for Sibyl

This script:
1. Parses all Python files in sibyl/ using AST
2. Builds an import dependency graph
3. Detects circular imports (strongly connected components)
4. Checks layering violations (core→framework, framework→techniques, etc.)
5. Generates a detailed report
"""

import ast
import json
import sys
from collections import defaultdict, deque
from pathlib import Path


class ImportGraph:
    """Build and analyze import dependency graph."""

    def __init__(self, root_path: Path) -> None:
        self.root_path = root_path
        self.sibyl_path = root_path / "sibyl"
        # Map: module_name -> set of imported modules
        self.imports: dict[str, set[str]] = defaultdict(set)
        # Map: file_path -> module_name
        self.file_to_module: dict[Path, str] = {}
        # Map: module_name -> file_path
        self.module_to_file: dict[str, Path] = {}

    def get_module_name(self, file_path: Path) -> str:
        """Convert file path to module name."""
        try:
            rel_path = file_path.relative_to(self.root_path)
        except ValueError:
            return ""

        parts = list(rel_path.parts)

        # Remove .py extension
        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]

        # Remove __init__ but keep the package name
        if parts[-1] == "__init__":
            parts = parts[:-1]

        return ".".join(parts) if parts else ""

    def resolve_import(self, base_module: str, import_name: str, level: int) -> str:
        """Resolve relative imports to absolute module names."""
        if level == 0:
            # Absolute import
            return import_name

        # Relative import
        base_parts = base_module.split(".")

        # Go up 'level' directories
        if level > len(base_parts):
            # Invalid relative import
            return import_name

        target_parts = base_parts[:-level] if level > 0 else base_parts

        if import_name:
            target_parts.append(import_name)

        return ".".join(target_parts)

    def parse_file(self, file_path: Path) -> None:
        """Parse a Python file and extract imports."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return
        except Exception:
            return

        module_name = self.get_module_name(file_path)
        if not module_name:
            return

        self.file_to_module[file_path] = module_name
        self.module_to_file[module_name] = file_path

        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported = alias.name.split(".")[0]  # Get top-level package
                    if imported == "sibyl":
                        self.imports[module_name].add(alias.name)

            elif isinstance(node, ast.ImportFrom) and node.module:
                module = node.module
                level = node.level

                # Resolve relative imports
                resolved = self.resolve_import(module_name, module, level) if level > 0 else module

                # Only track sibyl imports
                if resolved.startswith("sibyl"):
                    self.imports[module_name].add(resolved)

                    # Also add submodule imports
                    for alias in node.names:
                        if alias.name != "*":
                            submodule = f"{resolved}.{alias.name}"
                            # Only add if it could be a module (not obviously a class/function)
                            self.imports[module_name].add(submodule)

    def scan_directory(self) -> None:
        """Scan all Python files in sibyl/ directory."""
        for file_path in self.sibyl_path.rglob("*.py"):
            self.parse_file(file_path)

    def find_cycles(self) -> list[list[str]]:
        """Find all cycles using Tarjan's algorithm (SCC detection)."""
        index_counter = [0]
        stack = []
        lowlinks = {}
        index = {}
        on_stack = defaultdict(bool)
        sccs = []

        def strongconnect(node) -> None:
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)
            on_stack[node] = True

            # Consider successors
            for successor in self.imports.get(node, []):
                # Only consider modules we know about
                if successor not in self.module_to_file:
                    continue

                if successor not in index:
                    # Successor has not yet been visited
                    strongconnect(successor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[successor])
                elif on_stack[successor]:
                    # Successor is in stack and hence in current SCC
                    lowlinks[node] = min(lowlinks[node], index[successor])

            # If node is a root node, pop the stack and yield an SCC
            if lowlinks[node] == index[node]:
                component = []
                while True:
                    successor = stack.pop()
                    on_stack[successor] = False
                    component.append(successor)
                    if successor == node:
                        break

                # Only keep SCCs with more than one node (actual cycles)
                if len(component) > 1:
                    sccs.append(component)

        for node in self.module_to_file:
            if node not in index:
                strongconnect(node)

        return sccs

    def trace_cycle_path(self, cycle: list[str]) -> list[tuple[str, str]]:
        """Trace the actual import path in a cycle."""
        edges = []
        cycle_set = set(cycle)

        for i, module in enumerate(cycle):
            next_module = cycle[(i + 1) % len(cycle)]

            # Find if there's a direct import
            if next_module in self.imports.get(module, set()):
                edges.append((module, next_module))
            else:
                # Find an indirect path through other modules in the cycle
                # Use BFS to find shortest path
                queue = deque([(module, [module])])
                visited = {module}
                found = False

                while queue and not found:
                    current, path = queue.popleft()

                    for neighbor in self.imports.get(current, set()):
                        if neighbor == next_module:
                            edges.append((module, next_module))
                            found = True
                            break

                        if neighbor in cycle_set and neighbor not in visited:
                            visited.add(neighbor)
                            queue.append((neighbor, [*path, neighbor]))

        return edges

    def check_layering_violations(self) -> dict[str, list[tuple[str, str]]]:
        """Check for layering violations based on rules."""
        violations = {
            "core_imports_framework": [],
            "core_imports_techniques": [],
            "framework_imports_techniques": [],
        }

        for module, imported_modules in self.imports.items():
            # Determine layer of source module
            if module.startswith("sibyl.core."):
                for imported in imported_modules:
                    if imported.startswith("sibyl.framework."):
                        violations["core_imports_framework"].append((module, imported))
                    elif imported.startswith("sibyl.techniques."):
                        violations["core_imports_techniques"].append((module, imported))

            elif module.startswith("sibyl.framework."):
                for imported in imported_modules:
                    if imported.startswith("sibyl.techniques."):
                        violations["framework_imports_techniques"].append((module, imported))

        return violations

    def generate_report(self) -> str:
        """Generate a comprehensive report."""
        lines = []
        lines.append("=" * 80)
        lines.append("SIBYL CIRCULAR IMPORT & LAYERING ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Total modules scanned: {len(self.module_to_file)}")
        lines.append(f"Total import relationships: {sum(len(v) for v in self.imports.values())}")
        lines.append("")

        # Find cycles
        cycles = self.find_cycles()
        lines.append(f"Circular import cycles found: {len(cycles)}")
        lines.append("")

        # Check layering violations
        violations = self.check_layering_violations()
        total_violations = sum(len(v) for v in violations.values())
        lines.append(f"Layering violations found: {total_violations}")
        lines.append("")

        # Detail cycles
        if cycles:
            lines.append("=" * 80)
            lines.append("CIRCULAR IMPORT CYCLES")
            lines.append("=" * 80)
            lines.append("")

            for i, cycle in enumerate(cycles, 1):
                lines.append(f"Cycle #{i} ({len(cycle)} modules involved)")
                lines.append("-" * 80)

                # Sort for consistent output
                sorted_cycle = sorted(cycle)
                for module in sorted_cycle:
                    lines.append(f"  - {module}")

                lines.append("")
                lines.append("  Import chain:")

                # Try to trace a path through the cycle
                edges = self.trace_cycle_path(sorted_cycle)
                if edges:
                    for src, dst in edges:
                        lines.append(f"    {src}")
                        lines.append(f"      -> {dst}")
                else:
                    # Just show interconnections
                    for module in sorted_cycle:
                        imports_in_cycle = [
                            m for m in self.imports.get(module, set()) if m in cycle
                        ]
                        if imports_in_cycle:
                            lines.append(f"    {module} imports:")
                            for imp in sorted(imports_in_cycle):
                                lines.append(f"      -> {imp}")

                lines.append("")

        # Detail layering violations
        if total_violations > 0:
            lines.append("=" * 80)
            lines.append("LAYERING VIOLATIONS")
            lines.append("=" * 80)
            lines.append("")

            if violations["core_imports_framework"]:
                lines.append(
                    f"CRITICAL: core/ imports framework/ ({len(violations['core_imports_framework'])} violations)"
                )
                lines.append("-" * 80)
                for src, dst in sorted(violations["core_imports_framework"]):
                    lines.append(f"  {src}")
                    lines.append(f"    -> {dst}")
                lines.append("")

            if violations["core_imports_techniques"]:
                lines.append(
                    f"CRITICAL: core/ imports techniques/ ({len(violations['core_imports_techniques'])} violations)"
                )
                lines.append("-" * 80)
                for src, dst in sorted(violations["core_imports_techniques"]):
                    lines.append(f"  {src}")
                    lines.append(f"    -> {dst}")
                lines.append("")

            if violations["framework_imports_techniques"]:
                lines.append(
                    f"WARNING: framework/ imports techniques/ ({len(violations['framework_imports_techniques'])} violations)"
                )
                lines.append("-" * 80)
                for src, dst in sorted(violations["framework_imports_techniques"]):
                    lines.append(f"  {src}")
                    lines.append(f"    -> {dst}")
                lines.append("")

        # Top offenders
        lines.append("=" * 80)
        lines.append("TOP OFFENDERS (modules involved in most cycles)")
        lines.append("=" * 80)
        lines.append("")

        module_cycle_count = defaultdict(int)
        for cycle in cycles:
            for module in cycle:
                module_cycle_count[module] += 1

        if module_cycle_count:
            top_offenders = sorted(module_cycle_count.items(), key=lambda x: x[1], reverse=True)[
                :20
            ]
            for module, count in top_offenders:
                lines.append(f"  {module}: {count} cycle(s)")
        else:
            lines.append("  No modules involved in cycles")

        lines.append("")

        # Module import statistics
        lines.append("=" * 80)
        lines.append("MODULES WITH MOST IMPORTS")
        lines.append("=" * 80)
        lines.append("")

        module_import_count = [(m, len(imports)) for m, imports in self.imports.items()]
        top_importers = sorted(module_import_count, key=lambda x: x[1], reverse=True)[:20]

        for module, count in top_importers:
            lines.append(f"  {module}: {count} import(s)")

        lines.append("")
        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)

        return "\n".join(lines)

    def export_json(self) -> dict:
        """Export data as JSON for further analysis."""
        cycles = self.find_cycles()
        violations = self.check_layering_violations()

        return {
            "summary": {
                "total_modules": len(self.module_to_file),
                "total_imports": sum(len(v) for v in self.imports.values()),
                "cycles_found": len(cycles),
                "layering_violations": sum(len(v) for v in violations.values()),
            },
            "cycles": [sorted(cycle) for cycle in cycles],
            "layering_violations": {
                k: [(src, dst) for src, dst in v] for k, v in violations.items()
            },
            "import_graph": {module: sorted(imports) for module, imports in self.imports.items()},
        }


def main() -> None:
    root_path = Path(__file__).parent.parent.parent

    graph = ImportGraph(root_path)
    graph.scan_directory()

    # Generate and print report
    report = graph.generate_report()

    # Save report to file
    report_path = root_path / "circular_imports_report.txt"
    with open(report_path, "w") as f:
        f.write(report)

    # Export JSON data
    json_path = root_path / "circular_imports_data.json"
    with open(json_path, "w") as f:
        json.dump(graph.export_json(), f, indent=2)

    # Exit with error code if issues found
    cycles = graph.find_cycles()
    violations = graph.check_layering_violations()
    if cycles or any(violations.values()):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

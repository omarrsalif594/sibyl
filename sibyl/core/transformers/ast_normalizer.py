"""AST cross-server transformer for normalizing AST Server and OXC Parser outputs.

This module provides transformers that normalize AST outputs from different
MCP providers (AST Server, OXC Parser, ast-grep) into a unified ASTArtifact
representation, enabling cross-server workflows and tool interoperability.

Key features:
- Normalize AST Server (Python-focused) outputs
- Normalize OXC Parser (JavaScript/TypeScript) outputs
- Map provider-specific node types to common types
- Preserve provider-specific metadata
- Support round-trip conversion

Example:
    from sibyl.core.transformers.ast_normalizer import (
        normalize_ast_server_response,
        normalize_oxc_parser_response,
        merge_asts
    )

    # Normalize AST Server response
    python_ast = normalize_ast_server_response(
        ast_server_result,
        source_file="example.py"
    )

    # Normalize OXC Parser response
    js_ast = normalize_oxc_parser_response(
        oxc_result,
        source_file="example.js"
    )

    # Use unified API
    for ast in [python_ast, js_ast]:
        functions = ast.query("FunctionDef")  # Works for both!
"""

from typing import Any

from sibyl.core.artifacts import ASTArtifact, ASTNode, Location

# Node type mappings from provider-specific to common types
AST_SERVER_TYPE_MAPPINGS = {
    # Python AST types → Common types
    "FunctionDef": "FunctionDef",
    "AsyncFunctionDef": "FunctionDef",
    "ClassDef": "ClassDef",
    "Module": "Module",
    "Import": "Import",
    "ImportFrom": "Import",
    "Assign": "Assignment",
    "AugAssign": "Assignment",
    "AnnAssign": "Assignment",
    "If": "Conditional",
    "For": "Loop",
    "While": "Loop",
    "Try": "TryBlock",
    "With": "WithBlock",
    "Return": "Return",
    "Call": "CallExpression",
    "BinOp": "BinaryExpression",
    "UnaryOp": "UnaryExpression",
    "Compare": "CompareExpression",
    "Attribute": "MemberExpression",
    "Name": "Identifier",
    "Constant": "Literal",
}

OXC_PARSER_TYPE_MAPPINGS = {
    # JavaScript/TypeScript AST types → Common types
    "FunctionDeclaration": "FunctionDef",
    "ArrowFunctionExpression": "FunctionDef",
    "FunctionExpression": "FunctionDef",
    "ClassDeclaration": "ClassDef",
    "ClassExpression": "ClassDef",
    "Program": "Module",
    "ImportDeclaration": "Import",
    "ExportNamedDeclaration": "Export",
    "ExportDefaultDeclaration": "Export",
    "VariableDeclaration": "Assignment",
    "IfStatement": "Conditional",
    "ForStatement": "Loop",
    "WhileStatement": "Loop",
    "DoWhileStatement": "Loop",
    "TryStatement": "TryBlock",
    "ReturnStatement": "Return",
    "CallExpression": "CallExpression",
    "BinaryExpression": "BinaryExpression",
    "UnaryExpression": "UnaryExpression",
    "MemberExpression": "MemberExpression",
    "Identifier": "Identifier",
    "Literal": "Literal",
}


def normalize_ast_server_response(
    response: dict[str, Any], source_file: str, preserve_original_types: bool = True
) -> ASTArtifact:
    """Normalize AST Server response to ASTArtifact.

    AST Server provides Python AST analysis. This function converts its
    response format to a unified ASTArtifact representation.

    Args:
        response: Raw response from AST Server (dict with AST tree)
        source_file: Source file path
        preserve_original_types: If True, keep original type in properties

    Returns:
        Normalized ASTArtifact

    Example:
        # From AST Server
        mcp_result = await mcp_adapter(
            provider="ast_server",
            tool="parse_file",
            params={"file_path": "example.py"}
        )

        ast = normalize_ast_server_response(
            mcp_result,
            source_file="example.py"
        )

        # Now use common API
        functions = ast.query("FunctionDef")
    """
    # Extract root node
    root_data = response.get("ast", response)

    # Normalize the tree recursively
    root_node = _normalize_ast_server_node(root_data, source_file, preserve_original_types)

    # Extract metadata
    metadata = {
        "provider": "ast_server",
        "language": "python",
        "original_format": "python_ast",
    }

    # Include any metadata from response
    if "metadata" in response:
        metadata.update(response["metadata"])

    return ASTArtifact(
        root=root_node, language="python", source_file=source_file, metadata=metadata
    )


def normalize_oxc_parser_response(
    response: dict[str, Any], source_file: str, preserve_original_types: bool = True
) -> ASTArtifact:
    """Normalize OXC Parser response to ASTArtifact.

    OXC Parser provides fast JavaScript/TypeScript AST parsing. This function
    converts its response format to a unified ASTArtifact representation.

    Args:
        response: Raw response from OXC Parser
        source_file: Source file path
        preserve_original_types: If True, keep original type in properties

    Returns:
        Normalized ASTArtifact

    Example:
        # From OXC Parser
        mcp_result = await mcp_adapter(
            provider="oxc_parser",
            tool="parse",
            params={"code": js_code, "language": "javascript"}
        )

        ast = normalize_oxc_parser_response(
            mcp_result,
            source_file="example.js"
        )

        # Now use common API
        functions = ast.query("FunctionDef")
    """
    # Extract root node
    root_data = response.get("ast", response.get("program", response))

    # Detect language
    language = response.get("language", "javascript")
    if language not in ["javascript", "typescript", "jsx", "tsx"]:
        language = "javascript"

    # Normalize the tree recursively
    root_node = _normalize_oxc_node(root_data, source_file, preserve_original_types)

    # Extract metadata
    metadata = {
        "provider": "oxc_parser",
        "language": language,
        "original_format": "oxc_ast",
    }

    # Include any metadata from response
    if "metadata" in response:
        metadata.update(response["metadata"])

    return ASTArtifact(
        root=root_node, language=language, source_file=source_file, metadata=metadata
    )


def merge_asts(*asts: ASTArtifact, merge_strategy: str = "separate_roots") -> ASTArtifact:
    """Merge multiple AST artifacts into a unified view.

    Useful for cross-language or cross-file analysis workflows.

    Args:
        *asts: Variable number of ASTArtifact instances
        merge_strategy: How to merge - one of:
            - "separate_roots": Keep all roots as children of a new Module node
            - "flatten": Flatten all nodes into single list (loses hierarchy)

    Returns:
        Merged ASTArtifact

    Raises:
        ValueError: If no ASTs provided or strategy invalid

    Example:
        # Merge Python and JavaScript ASTs
        python_ast = normalize_ast_server_response(py_result, "main.py")
        js_ast = normalize_oxc_parser_response(js_result, "main.js")

        merged = merge_asts(python_ast, js_ast, merge_strategy="separate_roots")

        # Query across both
        all_functions = merged.query("FunctionDef")
    """
    if not asts:
        msg = "At least one AST must be provided"
        raise ValueError(msg)

    if merge_strategy not in ["separate_roots", "flatten"]:
        msg = f"Invalid merge_strategy '{merge_strategy}'. Must be 'separate_roots' or 'flatten'"
        raise ValueError(msg)

    if len(asts) == 1:
        # Single AST - return copy
        return asts[0]

    if merge_strategy == "separate_roots":
        # Create a new Module node with all roots as children
        merged_root = ASTNode(
            type="Module",
            properties={"merged": True, "source_count": len(asts)},
            children=[ast.root for ast in asts],
        )

        # Combine metadata
        merged_metadata = {
            "merged": True,
            "sources": [{"file": ast.source_file, "language": ast.language} for ast in asts],
            "providers": list({ast.metadata.get("provider", "unknown") for ast in asts}),
        }

        return ASTArtifact(
            root=merged_root, language="mixed", source_file="<merged>", metadata=merged_metadata
        )

    # merge_strategy == "flatten" not implemented yet
    msg = "Flatten merge strategy not yet implemented"
    raise NotImplementedError(msg)


def compare_asts(
    ast1: ASTArtifact, ast2: ASTArtifact, compare_locations: bool = False
) -> dict[str, Any]:
    """Compare two ASTs for structural similarity.

    Useful for detecting code duplication, refactoring validation, or
    cross-language pattern matching.

    Args:
        ast1: First AST
        ast2: Second AST
        compare_locations: Whether to compare source locations (strict equality)

    Returns:
        Dictionary with comparison metrics:
        - structural_similarity: Float 0.0-1.0
        - common_node_types: List of node types present in both
        - unique_to_ast1: Node types only in ast1
        - unique_to_ast2: Node types only in ast2
        - total_nodes_ast1: Total node count
        - total_nodes_ast2: Total node count

    Example:
        # Compare Python function with JavaScript function
        py_ast = normalize_ast_server_response(py_result, "func.py")
        js_ast = normalize_oxc_parser_response(js_result, "func.js")

        comparison = compare_asts(py_ast, js_ast)
        print(f"Similarity: {comparison['structural_similarity']:.2%}")
    """
    # Collect node types from both ASTs
    types1 = _collect_node_types(ast1.root)
    types2 = _collect_node_types(ast2.root)

    # Calculate similarity
    common = types1 & types2
    union = types1 | types2

    structural_similarity = len(common) / len(union) if union else 0.0

    return {
        "structural_similarity": structural_similarity,
        "common_node_types": sorted(common),
        "unique_to_ast1": sorted(types1 - types2),
        "unique_to_ast2": sorted(types2 - types1),
        "total_nodes_ast1": _count_nodes(ast1.root),
        "total_nodes_ast2": _count_nodes(ast2.root),
    }


# Internal helpers


def _normalize_ast_server_node(
    node_data: dict[str, Any], source_file: str, preserve_original: bool
) -> ASTNode:
    """Recursively normalize AST Server node."""
    original_type = node_data.get("type", node_data.get("node_type", "Unknown"))
    normalized_type = AST_SERVER_TYPE_MAPPINGS.get(original_type, original_type)

    properties = {}
    if preserve_original:
        properties["original_type"] = original_type

    # Extract common properties
    if "name" in node_data:
        properties["name"] = node_data["name"]
    if "value" in node_data:
        properties["value"] = node_data["value"]
    if "operator" in node_data:
        properties["operator"] = node_data["operator"]

    # Extract location
    location = None
    if "lineno" in node_data and "col_offset" in node_data:
        location = Location(
            file=source_file,
            start_line=node_data["lineno"],
            start_column=node_data["col_offset"],
            end_line=node_data.get("end_lineno", node_data["lineno"]),
            end_column=node_data.get("end_col_offset", node_data["col_offset"]),
        )

    # Recursively process children
    children = []
    for child_data in node_data.get("children", node_data.get("body", [])):
        if isinstance(child_data, dict):
            children.append(_normalize_ast_server_node(child_data, source_file, preserve_original))

    return ASTNode(
        type=normalized_type, properties=properties, children=children, location=location
    )


def _normalize_oxc_node(
    node_data: dict[str, Any], source_file: str, preserve_original: bool
) -> ASTNode:
    """Recursively normalize OXC Parser node."""
    original_type = node_data.get("type", "Unknown")
    normalized_type = OXC_PARSER_TYPE_MAPPINGS.get(original_type, original_type)

    properties = {}
    if preserve_original:
        properties["original_type"] = original_type

    # Extract common properties
    if "name" in node_data:
        properties["name"] = node_data["name"]
    if "value" in node_data:
        properties["value"] = node_data["value"]
    if "operator" in node_data:
        properties["operator"] = node_data["operator"]
    if "id" in node_data and isinstance(node_data["id"], dict):
        properties["name"] = node_data["id"].get("name")

    # Extract location
    location = None
    if "loc" in node_data:
        loc = node_data["loc"]
        if "start" in loc and "end" in loc:
            location = Location(
                file=source_file,
                start_line=loc["start"].get("line", 1),
                start_column=loc["start"].get("column", 0),
                end_line=loc["end"].get("line", 1),
                end_column=loc["end"].get("column", 0),
            )

    # Recursively process children
    children = []
    # OXC uses various fields for children
    for field in ["body", "declarations", "expression", "consequent", "alternate"]:
        child_data = node_data.get(field)
        if isinstance(child_data, dict):
            children.append(_normalize_oxc_node(child_data, source_file, preserve_original))
        elif isinstance(child_data, list):
            for item in child_data:
                if isinstance(item, dict):
                    children.append(_normalize_oxc_node(item, source_file, preserve_original))

    return ASTNode(
        type=normalized_type, properties=properties, children=children, location=location
    )


def _collect_node_types(node: ASTNode) -> set:
    """Collect all node types in the tree."""
    types = {node.type}
    for child in node.children:
        types.update(_collect_node_types(child))
    return types


def _count_nodes(node: ASTNode) -> int:
    """Count total nodes in the tree."""
    count = 1
    for child in node.children:
        count += _count_nodes(child)
    return count


__all__ = [
    "compare_asts",
    "merge_asts",
    "normalize_ast_server_response",
    "normalize_oxc_parser_response",
]

"""AST Artifact for abstract syntax tree outputs.

This module provides typed artifacts for abstract syntax trees from MCP tools
like AST Server, OXC Parser, and ast-grep. It enables type-safe AST manipulation,
traversal, and querying.

Example:
    from sibyl.core.artifacts.ast import ASTArtifact, ASTNode, Location

    # Create from AST Server response
    ast = ASTArtifact.from_mcp_response(
        response=ast_result,
        language="python",
        source_file="example.py"
    )

    # Query for function definitions
    functions = ast.query("FunctionDef")

    # Traverse with visitor pattern
    def count_nodes(node):
        counter[node.type] += 1
    ast.traverse(count_nodes)

    # Find node at position
    node = ast.find_at_position(line=10, column=5)
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Location:
    """Source code location information.

    Attributes:
        file: Source file path
        start_line: Starting line number (1-indexed)
        start_column: Starting column number (0-indexed)
        end_line: Ending line number (1-indexed)
        end_column: Ending column number (0-indexed)

    Example:
        loc = Location(
            file="example.py",
            start_line=10,
            start_column=4,
            end_line=10,
            end_column=15
        )
    """

    file: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int


@dataclass
class ASTNode:
    """AST node with children and properties.

    Represents a single node in the abstract syntax tree. Nodes can have
    arbitrary properties and child nodes, forming a tree structure.

    Attributes:
        type: Node type (e.g., "FunctionDef", "ClassDeclaration", "BinaryExpression")
        properties: Node-specific properties (name, modifiers, operators, etc.)
        children: Child AST nodes
        location: Optional source code location

    Example:
        node = ASTNode(
            type="FunctionDef",
            properties={"name": "calculate", "async": False},
            children=[...],
            location=Location(...)
        )
    """

    type: str
    properties: dict[str, Any]
    children: list["ASTNode"] = field(default_factory=list)
    location: Location | None = None

    def get_child(self, node_type: str) -> Optional["ASTNode"]:
        """Get first child node of given type.

        Args:
            node_type: Node type to search for

        Returns:
            First matching child node, or None if not found

        Example:
            # Get function body
            body = function_node.get_child("Block")
        """
        for child in self.children:
            if child.type == node_type:
                return child
        return None

    def get_children(self, node_type: str) -> list["ASTNode"]:
        """Get all child nodes of given type.

        Args:
            node_type: Node type to search for

        Returns:
            List of matching child nodes (may be empty)

        Example:
            # Get all function parameters
            params = function_node.get_children("Parameter")
        """
        return [child for child in self.children if child.type == node_type]


@dataclass
class ASTArtifact:
    """Artifact for abstract syntax trees.

    This artifact provides a typed interface to AST data with traversal,
    querying, and position-based lookup capabilities.

    Attributes:
        root: Root AST node
        language: Programming language (e.g., "python", "javascript", "typescript")
        source_file: Optional source file path

    Example:
        ast = ASTArtifact(
            root=ASTNode(
                type="Module",
                properties={},
                children=[...]
            ),
            language="python",
            source_file="example.py"
        )

        # Query for classes
        classes = ast.query("ClassDef")
    """

    root: ASTNode
    language: str
    source_file: str | None = None

    def traverse(self, visitor: Callable[[ASTNode], None], order: str = "preorder") -> None:
        """Traverse AST with visitor pattern.

        Visits each node in the AST and calls the visitor function.
        Supports preorder (parent before children) and postorder (children before parent).

        Args:
            visitor: Function to call for each node
            order: Traversal order ("preorder" or "postorder")

        Raises:
            ValueError: If order is not "preorder" or "postorder"

        Example:
            # Count node types
            counter = {}
            def count_visitor(node):
                counter[node.type] = counter.get(node.type, 0) + 1

            ast.traverse(count_visitor)

            # Collect function names
            functions = []
            def function_visitor(node):
                if node.type == "FunctionDef":
                    functions.append(node.properties.get("name"))

            ast.traverse(function_visitor)
        """

        def _traverse_preorder(node: ASTNode) -> None:
            visitor(node)
            for child in node.children:
                _traverse_preorder(child)

        def _traverse_postorder(node: ASTNode) -> None:
            for child in node.children:
                _traverse_postorder(child)
            visitor(node)

        if order == "preorder":
            _traverse_preorder(self.root)
        elif order == "postorder":
            _traverse_postorder(self.root)
        else:
            msg = f"Invalid traversal order: {order}. Must be 'preorder' or 'postorder'."
            raise ValueError(msg)

    def query(self, pattern: str) -> list[ASTNode]:
        """Query nodes matching type pattern.

        Finds all nodes in the AST that match the given type pattern.
        This is a simple type-based query; more advanced pattern matching
        can be added in future versions.

        Args:
            pattern: Node type to search for (exact match)

        Returns:
            List of matching AST nodes (may be empty)

        Example:
            # Find all function definitions
            functions = ast.query("FunctionDef")

            # Find all class definitions
            classes = ast.query("ClassDef")

            # Find all binary expressions
            binops = ast.query("BinaryExpression")
        """
        results: list[ASTNode] = []

        def visitor(node: ASTNode) -> None:
            if node.type == pattern:
                results.append(node)

        self.traverse(visitor)
        return results

    def find_at_position(self, line: int, column: int) -> ASTNode | None:
        """Find node at source position.

        Finds the most specific (deepest) AST node that contains the given
        source position. Useful for IDE-like features (go-to-definition, hover).

        Args:
            line: Line number (1-indexed)
            column: Column number (0-indexed)

        Returns:
            Most specific AST node at position, or None if not found

        Example:
            # Find node at cursor position
            node = ast.find_at_position(line=10, column=5)
            if node:
                print(f"Node type: {node.type}")
                print(f"Properties: {node.properties}")
        """

        def _contains_position(node: ASTNode) -> bool:
            """Check if node's location contains the given position."""
            if node.location is None:
                return False

            loc = node.location

            # Check line range
            if not (loc.start_line <= line <= loc.end_line):
                return False

            # Check column range on start line
            if line == loc.start_line and column < loc.start_column:
                return False

            # Check column range on end line
            return not (line == loc.end_line and column > loc.end_column)

        result: ASTNode | None = None

        def visitor(node: ASTNode) -> None:
            nonlocal result
            if _contains_position(node):
                # Keep deepest (most specific) match
                # Deeper nodes have more children or are visited later in preorder
                if result is None or len(node.children) <= len(result.children):
                    result = node

        self.traverse(visitor)
        return result

    @classmethod
    def from_mcp_response(
        cls, response: dict[str, Any], language: str, source_file: str | None = None
    ) -> "ASTArtifact":
        """Create ASTArtifact from MCP AST parser response.

        Parses MCP AST tool responses (from AST Server, OXC Parser, ast-grep)
        into typed AST structures with location information.

        Args:
            response: Raw response from MCP AST parser tool
            language: Programming language (e.g., "python", "javascript")
            source_file: Optional source file path

        Returns:
            ASTArtifact instance

        Example:
            # Parse Python code
            result = await mcp_adapter(
                provider="ast_server",
                tool="parse_to_ast",
                params={"code": code, "language": "python"}
            )

            ast = ASTArtifact.from_mcp_response(
                result,
                language="python",
                source_file="example.py"
            )

        Note:
            Expected response format:
            {
                "ast": {
                    "type": "Module",
                    "properties": {...},
                    "children": [...],
                    "location": {
                        "start_line": 1,
                        "start_column": 0,
                        ...
                    }
                }
            }
        """

        def parse_node(node_data: dict[str, Any]) -> ASTNode:
            """Recursively parse AST node data."""
            # Parse location if present
            location = None
            if "location" in node_data:
                loc_data = node_data["location"]
                location = Location(
                    file=source_file or "",
                    start_line=loc_data.get("start_line", 0),
                    start_column=loc_data.get("start_column", 0),
                    end_line=loc_data.get("end_line", 0),
                    end_column=loc_data.get("end_column", 0),
                )

            # Parse children recursively
            children = []
            for child_data in node_data.get("children", []):
                children.append(parse_node(child_data))

            # Extract properties (exclude special keys)
            properties = {
                k: v for k, v in node_data.items() if k not in {"type", "children", "location"}
            }

            return ASTNode(
                type=node_data.get("type", "Unknown"),
                properties=properties,
                children=children,
                location=location,
            )

        # Parse root node from response
        root_data = response.get("ast", response)  # Some tools put AST at root
        root = parse_node(root_data)

        return cls(root=root, language=language, source_file=source_file)

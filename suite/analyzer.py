"""
Code analysis utilities for the Suite pytest plugin.
"""

import ast
import inspect
import textwrap
from typing import Any, Callable

from pydantic import BaseModel


def parse_docstring(docstring: str) -> dict[str, Any]:
    """Parse a docstring into structured information."""
    lines = docstring.strip().split("\n")

    # Initialize the result dictionary
    result: dict[str, Any] = {
        "short_description": "",
        "long_description": "",
        "params": [],
        "returns": {
            "type": None,
            "description": None,
        },
    }

    # Extract short description
    result["short_description"] = lines[0].strip()

    # Extract long description (if any)
    if len(lines) > 1:
        result["long_description"] = "\n".join(
            line.strip() for line in lines[1:] if line.strip()
        )

    # Simple parameter and return type extraction (assuming a specific format)
    for line in lines:
        line = line.strip()
        if line.startswith(":param"):
            parts = line.split(":")
            param_name = parts[1].strip()
            param_type = parts[2].strip() if len(parts) > 2 else "unknown"
            param_description = parts[3].strip() if len(parts) > 3 else ""
            result["params"].append(
                {
                    "name": param_name,
                    "type": param_type,
                    "description": param_description,
                }
            )
        elif line.startswith(":returns:"):
            parts = line.split(":")
            result["returns"]["type"] = parts[1].strip() if len(parts) > 1 else None
            result["returns"]["description"] = (
                parts[2].strip() if len(parts) > 2 else None
            )

    return result


class FunctionInfo(BaseModel):
    """Information about a function extracted for semantic testing."""

    name: str
    docstring: str | None
    source: str | None
    source_file: str | None
    line_number: int | None
    dependencies: list["FunctionInfo"] = []

    def __str__(self) -> str:
        return f"{self.name} ({self.source_file}:{self.line_number})"

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary representation."""
        return {
            "name": self.name,
            "docstring": self.docstring,
            "source": self.source,
            "source_file": self.source_file,
            "line_number": self.line_number,
            "dependencies": [dep.to_dict() for dep in self.dependencies],
        }


class FunctionCallVisitor(ast.NodeVisitor):
    """AST visitor to find function calls within a function."""

    def __init__(self):
        self.function_calls: set[str] = set()

    def visit_Call(self, node):
        """Visit a function call node."""
        if isinstance(node.func, ast.Name):
            # Direct function call: func()
            self.function_calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            # Method call: obj.method()
            if isinstance(node.func.value, ast.Name):
                # Simple attribute: obj.method()
                self.function_calls.add(f"{node.func.value.id}.{node.func.attr}")

        # Continue visiting child nodes
        self.generic_visit(node)


def extract_docstring(func: Callable) -> str | None:
    try:
        return inspect.getdoc(func)
    except TypeError:
        return ""


def extract_source(func: Callable) -> str | None:
    try:
        return inspect.getsource(func)
    except TypeError:
        # For methods implemented in C we can't get its source
        return None


def extract_source_file(func: Callable) -> str | None:
    try:
        return inspect.getfile(func)
    except TypeError:
        return None


def extract_line_number(func: Callable) -> int | None:
    try:
        return inspect.getsourcelines(func)[1]
    except TypeError:
        return None


def extract_function_info(func: Callable) -> FunctionInfo:
    """Extract information about a function."""
    name = func.__name__
    docstring = extract_docstring(func)
    source = extract_source(func)
    source_file = extract_source_file(func)
    line_number = extract_line_number(func)

    return FunctionInfo(
        name=name,
        docstring=docstring,
        source=source,
        source_file=source_file,
        line_number=line_number,
    )


def find_function_calls(func: Callable) -> set[str]:
    """Find all function calls within a function.

    Args:
        func (Callable): function from which we want to extract calls

    Returns:
        set[str]: set with function names used in func
    """
    source = extract_source(func)
    if source:
        tree = ast.parse(textwrap.dedent(source))
        visitor = FunctionCallVisitor()
        visitor.visit(tree)
        return visitor.function_calls
    return set()


def get_function_by_name(name: str, module: object) -> Any | None:
    """Get a function object by name from a module.

    Args:
        name (str): _description_
        module (_type_): _description_

    Returns:
        Any | None: _description_
    """
    if hasattr(module, name):
        return getattr(module, name)

    # Handle dot notation (e.g., "module.function")
    parts = name.split(".")
    if len(parts) > 1:
        obj = module
        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return None
        return obj

    # Check if the function is imported from another module
    for key, value in module.__dict__.items():
        if key == name and callable(value):
            return value

    return None


def build_dependency_tree(
    func: Callable,
    max_depth: int = 2,
    current_depth: int = 0,
    visited: set[str] | None = None,
) -> FunctionInfo:
    """
    Build a dependency tree for a function.

    Args:
        func: The function to analyze
        max_depth: Maximum depth for dependency analysis
        current_depth: Current depth in the recursion
        visited: Set of already visited function names

    Returns:
        FunctionInfo object with dependencies
    """
    if visited is None:
        visited = set()

    func_info = extract_function_info(func)
    func_key = f"{func_info.source_file}:{func_info.name}"

    # Avoid circular dependencies
    if func_key in visited:
        return func_info

    visited.add(func_key)

    # Stop recursion if we've reached the maximum depth
    if current_depth >= max_depth:
        return func_info

    # Find function calls
    function_calls = find_function_calls(func)

    # Get the module of the function
    module = inspect.getmodule(func)

    # Recursively analyze dependencies
    for call_name in function_calls:
        dep_func = get_function_by_name(call_name, module)
        if dep_func and callable(dep_func):
            try:
                dep_info = build_dependency_tree(
                    dep_func, max_depth, current_depth + 1, visited
                )
                func_info.dependencies.append(dep_info)
            except (OSError, TypeError):
                # Skip dependencies that can't be analyzed
                pass

    return func_info

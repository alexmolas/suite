"""
Code analysis utilities for the Suite pytest plugin.
"""

import ast
import inspect
import textwrap
from typing import Any, Callable

from pydantic import BaseModel


class FunctionInfo(BaseModel):
    """Information about a function extracted for semantic testing."""

    name: str
    docstring: str | None
    source: str | None
    source_file: str | None
    dependencies: list["FunctionInfo"] = []

    @classmethod
    def from_func(
        cls,
        func: Callable,
        max_depth: int = 2,
        current_depth: int = 0,
        visited: set[str] = None,
    ):
        if visited is None:
            visited = set()

        name = func.__name__
        docstring = extract_docstring(func)
        source = extract_source(func)
        source_file = extract_source_file(func)

        # Stop recursion if we've reached the maximum depth
        if current_depth >= max_depth or name in visited:
            return cls(
                name=name,
                docstring=docstring,
                source=source,
                source_file=source_file,
                dependencies=[],
            )

        # Mark this function as visited
        visited.add(name)

        # Find function calls to determine dependencies
        function_calls = find_function_calls(func)
        dependencies = []

        for call in function_calls:
            dep_func = get_function_by_name(call, inspect.getmodule(func))
            if dep_func and callable(dep_func):
                # Recursively get dependencies
                dep_info = cls.from_func(
                    dep_func, max_depth, current_depth + 1, visited
                )
                dependencies.append(dep_info)

        return cls(
            name=name,
            docstring=docstring,
            source=source,
            source_file=source_file,
            dependencies=dependencies,
        )


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
        return None


def extract_source(func: Callable) -> str | None:
    try:
        return inspect.getsource(func)
    except TypeError:
        return None


def extract_source_file(func: Callable) -> str | None:
    try:
        return inspect.getfile(func)
    except TypeError:
        return None


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

    func_info = FunctionInfo.from_func(func)
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

"""
Code analysis utilities for the Suite pytest plugin.
"""

import ast
import inspect
import textwrap
from typing import Any, Callable

from pydantic import BaseModel


def get_callable_name(func: Callable) -> str:
    if inspect.isclass(func):
        return func.__name__
    elif inspect.isfunction(func):
        return func.__name__
    elif isinstance(func, object):
        return func.__class__.__name__
    raise ValueError(f"Couldn't extract the name of the object {func}")


class FunctionInfo(BaseModel):
    """
    Represents metadata and dependency information about a Python function.

    This class is used to extract and store semantic details about a callable,
    including its name, docstring, source code, source file location, and any
    other functions it depends on (via static analysis of function calls).

    Attributes:
        name (str): The name of the function.
        docstring (str | None): The docstring of the function, if available.
        source (str | None): The full source code of the function, if retrievable.
        source_file (str | None): The file path where the function is defined.
        dependencies (list[FunctionInfo]): A list of `FunctionInfo` objects representing
            other functions called by this function (dependencies), determined statically.

    Class Methods:
        from_func(func, max_depth=2, current_depth=0, visited=None, skip_implementation=False):
            Constructs a `FunctionInfo` object from a Python callable, with optional
            recursive analysis of its dependencies.

    Example:
        >>> def foo(): pass
        >>> FunctionInfo.from_func(foo)
        FunctionInfo(name='foo', docstring=None, ...)
    """

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
        visited: set[str] | None = None,
    ) -> "FunctionInfo":
        """
        Create a `FunctionInfo` instance from a Python function, with optional
        recursive analysis of its function-call dependencies.

        This method uses introspection and AST analysis to extract metadata about
        the given function and any other functions it calls (dependencies), up to a
        specified recursion depth.

        Args:
            func (Callable): The function to analyze.
            max_depth (int, optional): Maximum depth of dependency analysis. Defaults to 2.
            current_depth (int, optional): Internal parameter used for tracking the
                current recursion depth. Defaults to 0.
            visited (set[str] | None, optional): Set of function names already visited to
                avoid circular dependencies. Defaults to None.

        Returns:
            FunctionInfo: An object containing metadata about the function and its dependencies.

        Raises:
            ValueError: If the function name cannot be determined.

        Example:
            >>> def foo(): pass
            >>> FunctionInfo.from_func(foo)
            FunctionInfo(name='foo', docstring=None, ...)
        """
        if visited is None:
            visited = set()
        name = get_callable_name(func)
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
    except TypeError or OSError:
        return None


def extract_source(func: Callable) -> str | None:
    try:
        return inspect.getsource(func)
    except:
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

# Sample function for testing
from suite import format_dependencies, format_prompt
from suite.analyzer import FunctionInfo


def sample_function_a():
    """This is a sample function A."""
    pass


def sample_function_b():
    """This is a sample function B."""
    sample_function_a()


def test_format_dependencies():
    func_info = FunctionInfo.from_func(sample_function_b)
    formatted = format_dependencies(func_info)

    assert "Dependency 1: sample_function_a" in formatted
    assert "Docstring: This is a sample function A." in formatted
    assert "Implementation:" in formatted  # Check if source is included


def test_format_prompt():
    func_info = FunctionInfo.from_func(sample_function_b)
    formatted = format_prompt(func_info)

    assert "Function name: sample_function_b" in formatted
    assert "Docstring: This is a sample function B." in formatted
    assert "Dependencies:" in formatted  # Check if dependencies section is included
    assert "Implementation:" in formatted  # Check if source is included

from suite.analyzer import (
    FunctionInfo,
    find_function_calls,
)


# Sample functions for testing
def sample_function_a():
    pass


def sample_function_b():
    sample_function_a()


def sample_function_c():
    sample_function_b()


def sample_function_d():
    pass


def sample_function_e():
    sample_function_e()


def test_function_info():
    func_info = FunctionInfo.from_func(sample_function_a)
    assert func_info.name == "sample_function_a"
    assert func_info.docstring is None
    assert func_info.source is not None
    assert func_info.source_file is not None
    assert func_info.dependencies == []


def test_function_info_recursive():
    func_info = FunctionInfo.from_func(sample_function_e)
    assert func_info.name == "sample_function_e"
    assert func_info.docstring is None
    assert func_info.source is not None
    assert func_info.source_file is not None
    assert len(func_info.dependencies) == 1


def test_find_function_calls():
    calls = find_function_calls(sample_function_b)
    assert "sample_function_a" in calls
    assert len(calls) == 1


def test_build_dependency_tree():
    func_info = FunctionInfo.from_func(sample_function_c, max_depth=2)
    assert func_info.name == "sample_function_c"
    assert len(func_info.dependencies) == 1  # sample_function_b
    assert func_info.dependencies[0] == FunctionInfo.from_func(sample_function_b)
    assert len(func_info.dependencies[0].dependencies) == 1  # sample_function_a
    assert func_info.dependencies[0].dependencies[0] == FunctionInfo.from_func(
        sample_function_a
    )


def test_build_dependency_tree_recursive():
    func_info = FunctionInfo.from_func(sample_function_e, max_depth=10)
    assert func_info.name == "sample_function_e"
    assert len(func_info.dependencies) == 1


def test_no_dependencies():
    func_info = FunctionInfo.from_func(sample_function_d, max_depth=2)
    assert func_info.name == "sample_function_d"
    assert func_info.dependencies == []

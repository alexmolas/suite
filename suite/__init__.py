import json
import logging
from typing import Callable
import llm
from pydantic import BaseModel

from suite.analyzer import FunctionInfo


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


DEFAULT_SYSTEM_PROMPT = """
You are an AI assistant designed to evaluate the correctness of function implementations against their docstrings. 
Your task is to analyze the provided function, its docstring, and any dependencies to determine if the implementation meets the described behavior. 
Please provide a detailed reasoning for your evaluation.
"""

DEFAULT_PROMPT_TEMPLATE = """
You are evaluating whether a function implementation correctly matches its docstring.

Function name: {function_name}
Docstring: {docstring}
Implementation: {source}
Dependencies: {dependencies}

Does the implementation correctly fulfill what is described in the docstring?
Read the implementation carefully. Reason step by step and take your time.
"""


DEFAULT_DEPENDENCY_TEMPLATE = """
Dependency {index}: {function_name}
Docstring: {docstring}
Implementation: {source}
"""


def format_dependencies(
    func_info: FunctionInfo, dependencies_template: str = DEFAULT_DEPENDENCY_TEMPLATE
) -> str:
    """
    Format dependency information for inclusion in the prompt.

    Args:
        func_info: Function information with dependencies
        template: Template for formatting dependencies

    Returns:
        Formatted dependency context string
    """
    if not func_info.dependencies:
        return "No dependencies found."

    context = []

    def format_dep(dep: FunctionInfo, index: str) -> str:
        """Recursively format a dependency and its dependencies."""
        dep_context = dependencies_template.format(
            index=index,
            function_name=dep.name,
            docstring=dep.docstring,
            source=dep.source,
        )
        # Format nested dependencies
        if dep.dependencies:
            nested_context = []
            for i, nested_dep in enumerate(dep.dependencies, 1):
                nested_index = f"{index}.{i}"  # Create hierarchical index
                nested_context.append(format_dep(nested_dep, nested_index))
            dep_context += "\n" + "\n".join(nested_context)
        return dep_context

    for i, dep in enumerate(func_info.dependencies, 1):
        index = str(i)  # Top-level index
        context.append(format_dep(dep, index))

    return "\n".join(context)


def format_prompt(
    func_info: FunctionInfo,
    prompt_template: str = DEFAULT_PROMPT_TEMPLATE,
    dependencies_template: str = DEFAULT_DEPENDENCY_TEMPLATE,
) -> str:
    """
    Format a prompt for the LLM.

    Args:
        func_info: Function information
        template: Prompt template

    Returns:
        Formatted prompt
    """
    dependencies = format_dependencies(func_info, dependencies_template)
    return prompt_template.format(
        function_name=func_info.name,
        docstring=func_info.docstring,
        source=func_info.source,
        dependencies=dependencies,
    )


class SuiteOutput(BaseModel):
    reasoning: str
    passed: bool

    def __bool__(self):
        return self.passed


def _process_resp(text: str) -> dict:
    return json.loads(text)


class suite:
    """A class that evaluates a function using semantic testing suite using an LLM model."""

    def __init__(
        self,
        model_name: str,
        max_depth: int = 1,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        prompt_template: str = DEFAULT_PROMPT_TEMPLATE,
        dependencies_template: str = DEFAULT_DEPENDENCY_TEMPLATE,
        debug=False,
    ):
        self.model_name = model_name
        self.model = llm.get_model(model_name)
        self.max_depth = max_depth
        self.system_prompt = system_prompt
        self.prompt_template = prompt_template
        self.dependencies_template = dependencies_template
        self.debug = debug

    def __call__(self, func: Callable) -> SuiteOutput:
        """Evaluate the function against its docstring using the LLM model.

        Args:
            func (Callable): The function to evaluate.

        Returns:
            SuiteOutput: The result of the evaluation, including reasoning and pass/fail status.
        """
        func_info = FunctionInfo.from_func(func, max_depth=self.max_depth)
        prompt = format_prompt(
            func_info, self.prompt_template, self.dependencies_template
        )
        if self.debug:
            logger.info(prompt)
        resp = self.model.prompt(
            prompt=prompt, system=self.system_prompt, schema=SuiteOutput
        ).text()
        if self.debug:
            logger.info(resp)
        return SuiteOutput(**_process_resp(resp))


class async_suite:
    """An class that asynchronously evaluates a function using semantic testing suite using an LLM model."""

    def __init__(
        self,
        model_name: str,
        max_depth: int = 1,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        prompt_template: str = DEFAULT_PROMPT_TEMPLATE,
        dependencies_template: str = DEFAULT_DEPENDENCY_TEMPLATE,
        debug=False,
    ):
        self.model_name = model_name
        self.model = llm.get_async_model(model_name)  # Use async model
        self.max_depth = max_depth
        self.system_prompt = system_prompt
        self.prompt_template = prompt_template
        self.dependencies_template = dependencies_template
        self.debug = debug

    async def __call__(self, func: Callable) -> SuiteOutput:
        """
        Evaluate the function against its docstring asynchronously using the LLM model.

        Args:
            func (Callable): The function to evaluate.

        Returns:
            SuiteOutput: The result of the evaluation, including reasoning and pass/fail status.
        """

        func_info = FunctionInfo.from_func(func, max_depth=self.max_depth)
        prompt = format_prompt(
            func_info, self.prompt_template, self.dependencies_template
        )
        if self.debug:
            logger.info(prompt)
        resp = await self.model.prompt(
            prompt=prompt, system=self.system_prompt, schema=SuiteOutput
        ).text()  # Await the async call
        if self.debug:
            logger.info(resp)

        return SuiteOutput(**_process_resp(resp))

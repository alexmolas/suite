# Semantic Unit Testing

## What's semantic unit testing?

Semantic unit testing is a testing approach that evaluates whether a function's implementation aligns with its documented behavior. The code is analyzed using LLMs to assess whether the implementation matches the expected behavior described in the docstring.

Here's an example of how to use it


```python
from suite import suite

tester = suite(model_name="openai/o3-mini")

def multiply(x: int, y: int):
    """Multiplies x by y

    Args:
        x (int): value
        y (int): value
    """
    return x + y

result = tester(multiply)
print(result)

# {'reasoning': "The function's docstring states that it should multiply x by y. 
#   However, the implementation returns x + y, which is addition instead of multiplication. 
#   Therefore, the implementation does not correctly fulfill what is described in the docstring.",
# 'passed': False}
```

In this example, the implementation of `multiply` contains an error (it uses addition instead of multiplication). When the `tester` is called with the `multiply` function, it evaluates the implementation against the docstring, providing feedback on any discrepancies. This process helps ensure that the function behaves as expected and adheres to its documentation.


## Why?

- **Comprehensive Coverage**: Traditional unit testing focuses on specific inputs and outputs, covering only a small surface of the code. `suite`, on the other hand, evaluates the semantic correctness of functions by analyzing their implementation against their documentation.
- **No need to write tests by hand**: Writing tests by hand can be tiring and non-exhaustive. By using LLMs, we can avoid having to write specific examples one by one. This not only saves time but also ensures that a wider range of scenarios and edge cases are considered, leading to more robust testing outcomes.
- **Enhanced Reasoning with LLMs**: By passing code and context to LLMs, Suite enables a deeper level of reasoning about the function's behavior. This capability allows for more nuanced evaluations.


## How?

This library uses [llm](https://llm.datasette.io/en/stable/) package by [Simon Willison](https://simonwillison.net/). When testing a method, its source code, docstring, and the dependencies information (any other method used by the code under testing) are retrieved and passed to an LLM for evaluation. Then, the LLM decides if the evaluation is correct or not.

Since we're using llm library we can use any supported model. From my experience, reasoning models that support structured outputs are the ones that work the best (eg: `o3-mini`). 


## Usage

To use the `suite` module, you can create an instance of the `suite` or `async_suite` class, depending on your needs. You will then pass the function you want to test, and `suite` will evaluate its implementation against its docstring, providing feedback on any discrepancies.

You have a couple of examples in the `examples` folder.

The intended usage of this package is for testing, so you could do something like


```python
# tests/test_multiply.py

from package import multiply
from suite import suite

tester = suite(model="openai/o3-mini")

def test_multiply():
    assert tester(multiply)
```

Since `suite` also supports async operations you can use `pytest-asyncio` to speed up your tests (you don't need to run them sequentially since the bottlenck is not your laptop but the LLM provider).

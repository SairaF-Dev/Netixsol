# LangChain Agent

A LangChain implementation of the raw-Python agent built in Week 5 Day 1. This project demonstrates how LangChain provides abstractions for tool calling, agent execution, LCEL pipelines, conversation history, structured output, and tool-error handling.

## Overview

The agent uses **Groq** as the model provider through LangChain's `langchain-groq` integration.

The notebook covers:

* LangChain setup and core concepts
* Mapping raw-Python agent components to LangChain
* LCEL prompt → model → parser pipelines
* Custom tools using the `@tool` decorator
* A local JSON product database
* Tool-calling agents with `AgentExecutor`
* Multi-tool execution
* Conversation history with `RunnableWithMessageHistory`
* Structured output using Pydantic
* Tool failure testing and recovery
* Comparison between the raw-Python and LangChain implementations

## Project Structure

```text
week5-day2/
│
├── langchain_agent.ipynb          — working LangChain agent notebook
├── products.json                  — local product data source
├── .gitignore                         — files excluded from Git (including .env)
├── README.md                      — project documentation
└── raw_python_vs_langchain.pdf   — one-page comparison and annotated trace
```

## Requirements

* Python 3.10+
* A Groq API key
* Jupyter Notebook or JupyterLab

## Installation

Install the required packages:

```bash
pip install langchain langchain-groq langchain-core pydantic python-dotenv
```

## Environment Configuration

Create a `.env` file in the project directory:

```text
GROQ_API_KEY=your-key-here
```

Replace `your-key-here` with your actual Groq API key.

Do not commit the `.env` file or expose the API key publicly.

## Tools

The agent uses three normal tools:

### `calculator`

Evaluates restricted arithmetic expressions without using Python's `eval()`.

Supported operations include:

* Addition
* Subtraction
* Multiplication
* Division
* Exponentiation
* Unary `+` and `-`
* Parentheses

### `get_weather`

Provides demo weather information for:

* Lahore
* Karachi
* Islamabad

The weather data is stored in a fixed local dictionary and is intended as a demonstration tool rather than a live weather API.

### `get_product_price`

Reads product prices and specifications from the local `products.json` file.

This tool is used in the memory demonstration to:

1. Find the price of Laptop A.
2. Compare Laptop A with Laptop B.
3. Recommend a product for a budget-conscious client.

### `failing_product_lookup`

A separate testing tool that deliberately raises a `RuntimeError`.

It is used only for the error-handling experiment and is not included in the normal agent's tool list.

## Tool Docstrings

The tools are defined using LangChain's `@tool` decorator.

LangChain uses the function name, type hints, and docstring to build the tool schema provided to the model. The docstring becomes the tool description, helping the model understand what the tool does and when it should be used.

Therefore, clear tool docstrings are important for reliable tool selection. LangChain reduces the need to manually construct tool schemas, but the developer is still responsible for providing accurate tool descriptions.

## LCEL

The notebook demonstrates LangChain Expression Language using a simple pipeline:

```python
prompt | llm | StrOutputParser()
```

The pipe operator composes the components into a sequential runnable pipeline. The prompt formats the input, the model generates the response, and the output parser processes the model response into the required format.

## Agent Execution

The main agent uses:

```python
create_tool_calling_agent()
```

and:

```python
AgentExecutor()
```

`AgentExecutor` manages the agent's tool-calling and execution loop instead of requiring a manually implemented `while` loop like the Day 1 raw-Python agent.

`verbose=True` is enabled during demonstrations so that tool invocations, tool results, and execution status can be observed.

The model's private reasoning is not exposed as a raw chain-of-thought trace. The notebook therefore annotates the observable tool-calling sequence as **ACT → OBSERVE → FINAL**.

## Conversation History

Conversation history is implemented using:

```python
RunnableWithMessageHistory
```

A three-turn scenario demonstrates that the agent can maintain context between requests:

```text
Turn 1:
Find the price of Laptop A.

Turn 2:
Now compare it to Laptop B.

Turn 3:
Which one should I recommend to a budget-conscious client?
```

The conversation history allows references such as `"it"` and `"which one"` to be interpreted using previous turns.

Memory and tool retrieval remain separate concerns: conversation history provides previous conversational context, while the agent may call a tool again when it needs current product information.

## Structured Output

The notebook uses LangChain's structured-output support with a Pydantic model:

```python
class Recommendation(BaseModel):
    recommended_product: str
    price: float
    reason: str
```

The structured-output mechanism produces a validated `Recommendation` object containing:

* `recommended_product`
* `price`
* `reason`

This provides a predictable schema that can be consumed programmatically instead of relying only on free-form text.

## Error Handling

A deliberate failure is created using a `failing_product_lookup` tool that raises a `RuntimeError`.

Two approaches are tested:

1. **Unhandled failure:** the broken tool raises an exception, which propagates and stops the agent execution.
2. **Graceful recovery:** a safe version of the tool catches the exception using `try/except` and returns a controlled `TOOL_ERROR` message.

The agent receives the `TOOL_ERROR` as a tool observation and follows the system instructions not to invent product information. It then completes normally and returns a graceful response instead of terminating with an exception.

The experiment also showed that `handle_tool_errors=True` alone was not sufficient for the particular deliberately failing tool and LangChain setup used in this notebook. The successful recovery therefore uses **tool-level exception handling with `try/except` and a controlled `TOOL_ERROR` response**.

## Raw Python vs. LangChain

The Day 1 raw-Python implementation manually handled:

* Tool schemas
* Message history
* Tool execution
* The agent loop
* Reason → Act → Observe orchestration
* Error handling
* Logging

The LangChain implementation replaces much of this repetitive plumbing with framework abstractions:

| Raw Python                    | LangChain                              |
| ----------------------------- | -------------------------------------- |
| Manual tool schema            | `@tool`                                |
| Manual agent loop             | `AgentExecutor`                        |
| Manual message history        | `RunnableWithMessageHistory`           |
| Manual pipeline orchestration | LCEL                                   |
| Manual output formatting      | Pydantic structured output             |
| Tool-level exception handling | `try/except` + controlled `TOOL_ERROR` |

The main trade-off is that LangChain reduces implementation effort while hiding some lower-level execution details that were directly visible in the raw-Python implementation.

## Annotated Trace

A representative multi-tool execution follows this pattern:

```text
[START]
AgentExecutor chain begins.

[ACT]
get_weather("Lahore")

[OBSERVE]
41°C, sunny

[ACT]
get_product_price("Laptop A")

[OBSERVE]
$899, 16GB RAM, 512GB SSD, mid-range CPU

[FINAL]
Agent combines the tool results into the final answer.

[END]
AgentExecutor completes.
```

The `[ACT]`, `[OBSERVE]`, `[FINAL]`, and `[START]/[END]` labels above are annotations of the observed LangChain execution trace, not labels printed directly by LangChain.

`verbose=True` exposes tool invocations, tool results, and execution status. The model's private reasoning is not displayed.

## LangChain vs. Day 1

The Day 1 raw-Python implementation made the agent loop and tool-calling process explicit. The developer manually managed the model request, tool selection, tool execution, observations, and loop control.

LangChain automates many of these repeated patterns through `@tool`, `AgentExecutor`, LCEL, and `RunnableWithMessageHistory`. This makes the implementation shorter and easier to extend, but it also hides some execution details and introduces framework abstractions that must be understood when debugging unexpected behavior.

Building the raw-Python version first makes these LangChain abstractions easier to understand because their underlying responsibilities are already familiar.

## Learning Outcome

This project demonstrates that LangChain does not fundamentally change what an agent is. The underlying process remains a model deciding when to use tools, receiving tool results, and continuing until it can produce a final response.

The main difference is that LangChain packages repeated implementation patterns into reusable abstractions. Building the raw-Python version first makes these abstractions easier to understand and debug rather than treating the framework as "magic."

*Author: Saira Fatima | DevSquad '26 Internship at NetixSol*

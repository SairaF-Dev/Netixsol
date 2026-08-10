#  Agent Foundations

## Reasoning Loops, Tool Calling and Raw Python Agents

This project implements a minimal AI agent from scratch using Python and the Groq API through its OpenAI-compatible interface. The implementation does not use LangChain, LangGraph, CrewAI, or any other agent framework.

The purpose of this exercise is to understand the fundamental components of an AI agent before working with higher-level frameworks.

## Objectives

The project covers the following concepts:

* Agent, chatbot, and workflow differences
* ReAct reasoning loop
* LLM tool calling
* Function tool schemas
* Multi-step agent execution
* Conversation memory
* Working memory and agent state
* Logging and debugging
* Failure modes and guardrails
* Purpose of agent frameworks

## Technologies

* Python
* Groq API
* OpenAI Python SDK
* python-dotenv
* JSON Schema
* Jupyter Notebook

## Model

```text
openai/gpt-oss-20b
```

The OpenAI Python SDK is configured to use Groq's OpenAI-compatible API endpoint.

## Installation

Install the required dependencies:

```bash
pip install openai python-dotenv
```

## Environment Configuration

Create a `.env` file in the project directory:

```env
GROQ_API_KEY=your-groq-api-key
```

The API key is loaded using `python-dotenv`.

```python
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
```

API keys should never be hardcoded or committed to version control.

Add the following to `.gitignore`:

```gitignore
.env
__pycache__/
.ipynb_checkpoints/
```

## API Client Configuration

The project uses the OpenAI Python SDK with Groq's OpenAI-compatible endpoint.

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=api_key
)

MODEL = "openai/gpt-oss-20b"
```

# Task 1: Agent Concepts and Mental Model

## Agent vs Chatbot vs Workflow

### Chatbot

A chatbot generally receives a user message and generates a response using an LLM.

```text
User
  |
  v
LLM
  |
  v
Response
```

### Workflow

A workflow follows a predefined sequence of steps implemented by the developer.

```text
Input
  |
  v
Step 1
  |
  v
Step 2
  |
  v
Step 3
  |
  v
Output
```

### Agent

An agent allows the LLM to determine what action should be performed next based on the current task and previous observations.

```text
User Task
    |
    v
   LLM
    |
    v
 Tool Selection
    |
    v
Tool Execution
    |
    v
Observation
    |
    v
   LLM
    |
    v
Final Answer
```

An application becomes more agentic when it can select tools, perform multiple steps, use observations to determine subsequent actions, and adapt its behavior during execution.

## ReAct Pattern

The agent follows the ReAct pattern:

```text
REASON
   |
   v
 ACT
   |
   v
OBSERVE
   |
   v
REPEAT
```

The model first determines what needs to happen, selects an appropriate tool, receives the tool result, and then decides what to do next.

The loop continues until the model produces a final response or the maximum iteration limit is reached.

## When an Agent Is Overkill

An agent is unnecessary when a task can be solved using a simple prompt, deterministic function, or predefined workflow. Using an agent for straightforward operations introduces additional complexity, latency, and potential failure modes without providing meaningful benefits.

# Task 2: Tool Calling Fundamentals

Two tools are implemented in this project.

## Calculator Tool

The calculator accepts an arithmetic expression and evaluates supported operations.

Supported operations include:

```text
+
-
*
/
**
unary +/-
()
```

Example:

```text
(4 + 5) * 2
```

The calculator performs input validation and returns explicit error messages for unsupported expressions and invalid operations such as division by zero.

## Weather Tool

The weather tool accepts a city name and returns:

* Temperature in Celsius
* Weather condition

Example data:

```text
Lahore    41°C    Sunny
Karachi   34°C    Humid
```

The weather database is intentionally hardcoded because the tool is a stub for demonstrating tool calling. It is not a real-time weather service.

## Tool Schema

The tools use the OpenAI-compatible function calling format:

```python
{
    "type": "function",
    "function": {
        "name": "tool_name",
        "description": "Tool description",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}
```

Each schema clearly defines the expected arguments and required fields.

## Importance of Tool Descriptions

The LLM does not have direct access to the Python implementation of the tools. It receives the tool name, description, and parameter schema.

The description therefore acts as an interface contract. It informs the model when the tool should be used, what the tool does, and which arguments it requires.

Clear descriptions improve tool selection and reduce malformed or inappropriate tool calls.

# Task 3: Minimal Agent Loop

The agent is implemented using a Python `while` loop.

The execution process is:

```text
Send user message
      |
      v
Call LLM
      |
      v
Check for tool call
      |
      +------ No ------> Return final answer
      |
     Yes
      |
      v
Execute tool
      |
      v
Append tool result
      |
      v
Call LLM again
      |
      v
Repeat
```

A `max_iterations` safeguard is included to prevent the agent from running indefinitely.

## Multi Step Test

The agent was tested with the following task:

```text
Look up the weather in Lahore and Karachi,
then tell me which city is warmer and by how many degrees.
```

The agent performed the following steps:

```text
Iteration 1
get_weather("Lahore")
Result: 41°C

Iteration 2
get_weather("Karachi")
Result: 34°C

Iteration 3
Final Answer
```

The agent correctly determined that Lahore is warmer than Karachi by 7°C.

# Task 4: Memory and State Handling

## Conversation Memory

Conversation memory is maintained through the `messages` list.

It contains:

* User messages
* Assistant responses
* Assistant tool calls
* Tool results

This message history is sent back to the model during subsequent iterations.

## Working Memory

The agent maintains a separate `working_memory` structure:

```python
working_memory = {
    "iterations": 0,
    "tool_calls": [],
    "observations": [],
    "errors": []
}
```

This tracks the agent's execution state and provides useful information for debugging.

It records:

* Iteration count
* Tool calls
* Tool inputs
* Tool observations
* Errors

## Logging

The agent provides structured logging using labels such as:

```text
[MODEL]
[ACT]
[OBSERVE]
[ERROR]
[DONE]
[STOPPED]
```

This makes the reasoning process, tool execution, observations, and termination conditions easier to inspect during debugging.

# Task 5: Failure Modes and Guardrails

Several failure scenarios were tested.

## 1. Tool Error

The agent was asked:

```text
What's the weather like in Atlantis?
```

The weather tool returned:

```text
ERROR: no weather data available for city 'Atlantis'
```

The error was returned to the model, which then produced an appropriate response.

### Mitigation

Tools should return clear error messages instead of allowing exceptions to terminate the entire agent loop.

## 2. Unsupported Capability

The agent was asked to perform currency conversion, but no currency conversion tool was defined.

The model correctly identified that the required capability was unavailable instead of inventing a tool.

### Mitigation

Only expose supported tools and ensure the agent does not assume unavailable capabilities.

## 3. Ambiguous Request

The agent was asked:

```text
Is it nice outside?
```

The request did not specify a location.

The model asked for a city or location instead of making an unsupported assumption.

### Mitigation

Require necessary tool inputs and instruct the model to ask clarification questions when important information is missing.

## Additional Potential Failure Modes

### Infinite Loops

An agent may repeatedly call tools without reaching a final answer.

**Mitigation:** Use a `max_iterations` safeguard.

### Malformed Tool Arguments

The model may produce invalid JSON or incorrect argument values.

**Mitigation:** Validate and parse tool arguments defensively and use strict JSON schemas.

### Tool Execution Errors

A tool may fail during execution.

**Mitigation:** Use exception handling and return explicit error messages to the model.

### Context Growth

Long-running agents can accumulate large amounts of conversation history.

**Mitigation:** Summarize or prune unnecessary history while preserving important state in working memory.

# Why Agent Frameworks Exist

Frameworks such as LangChain, LangGraph, and CrewAI provide abstractions for the components implemented manually in this project.

A raw agent implementation requires developers to manage:

* Tool calling
* Tool dispatch
* State
* Memory
* Error handling
* Retries
* Logging
* Stopping conditions
* Multi-agent coordination
* Provider-specific API formats

Agent frameworks standardize these patterns and provide reusable abstractions for building larger and more complex systems.

Implementing the agent manually first provides a better understanding of what these frameworks are doing internally.

# Project Structure

```text
week5_day1/
│
├── agent_foundations.ipynb
├── README.md
├── .env
├── .gitignore
└── Week_5_Day_1_Agent_Foundations_Writeup.pdf
```

The `.env` file must not be committed to GitHub.

# Deliverables

* Agent concepts and mental model
* ReAct loop explanation
* Calculator tool
* Weather lookup stub
* JSON tool schemas
* Tool description explanation
* Single tool call demonstration
* Raw Python `while` loop agent
* Multi step agent demonstration
* `max_iterations` safeguard
* Conversation memory explanation
* Working memory implementation
* Structured logging
* Failure mode experiments
* Guardrails and mitigations
* Framework comparison
* One page PDF write up

# Key Takeaway

An AI agent can be understood as a model driven execution loop:

```text
REASON
   |
   v
ACT
   |
   v
OBSERVE
   |
   v
REASON
   |
   v
ACT
   |
   v
OBSERVE
   |
   v
FINAL ANSWER
```

Building this loop directly in Python provides the foundation required to understand higher level agent frameworks and their abstractions.

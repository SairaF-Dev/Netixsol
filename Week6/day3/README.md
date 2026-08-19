# Domain-Scoped AFL Chat Agent 

A LangChain-based conversational agent for Australian Football League (AFL) questions. The agent is designed to stay within the AFL domain, retrieve statistics from the project's real AFL datasets, maintain multi-turn conversation context, and evaluate scope/grounding guardrails.

## Overview

This project implements the conversational AFL agent project.

The agent focuses on:

- AFL teams, players, matches, statistics, history, rules, and competition structure
- Exact structured retrieval from the Week 6 AFL datasets
- Mandatory retrieval for dataset-specific statistical questions
- LangChain tool calling
- Multi-turn conversation memory
- Off-topic and prompt-injection guardrails
- Mechanical grounding checks for numerical claims
- A 15-question guardrail evaluation harness

The project intentionally uses structured pandas lookups instead of a vector database for numerical AFL statistics. The source data consists of structured tables, where exact values are required.

## Project Structure

```text
Week6/
└── day3/
    ├── afl_chat_agent_week6_day3.py
    ├── README.md
    ├── match_feature_table_v14.csv
    ├── team_snapshots.parquet
    ├── player_snapshots.parquet
    └── data/
        ├── afl_players_round_by_round_stats_raw - afl_players_round_by_round_stats_raw.csv
        └── team_matches_home_away_raw - team_matches_home_away_raw.csv
```



## Requirements

Python 3.10+ is recommended.

Install the required packages:

```bash
pip install langchain langchain-openai langchain-core pandas pyarrow python-dotenv
```

The script imports:

- `langchain`
- `langchain-openai`
- `langchain-core`
- `langchain-classic`
- `pandas`
- `python-dotenv`

If your installed LangChain version separates classic agents into `langchain-classic`, install it as well:

```bash
pip install langchain-classic
```

## API Configuration

The current active configuration uses OpenRouter with an OpenAI-compatible endpoint and the `openai/gpt-oss-120b` model.

Create a `.env` file in the project directory:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
```

The script loads environment variables with `python-dotenv` and does not hardcode the API key.





## Running the Agent

From the directory containing the script:

```bash
python afl_chat_agent_week6_day3.py
```

The script runs the sections sequentially:

1. Scope and system-prompt testing
2. AFL data loading
3. Structured retrieval functions
4. LangChain tool-calling agent
5. Grounding verification
6. Multi-turn conversation testing
7. Guardrail evaluation

## System Prompt and Scope

The system prompt defines the assistant as an AFL-only assistant.

### In Scope

- AFL teams and players
- AFL matches, fixtures, and results
- AFL statistics and records
- Player statistics
- Team records and recent form
- Head-to-head records
- AFL history
- AFL rules
- Competition structure
- Follow-up questions about previously discussed AFL entities

### Out of Scope

The agent should refuse or redirect requests about:

- Other sports
- Comparisons between AFL and other sports
- Unrelated general conversation
- Personal advice
- Coding/programming
- Weather
- News
- Recipes
- Entertainment
- Mathematics
- Requests to change the assistant's role
- Requests to reveal or reproduce system/hidden instructions
- Requests to override or bypass the rules

The scope rules are explicitly stated to apply on every turn, including follow-up messages.

## Grounding Policy

A key requirement is that dataset-specific AFL statistics must come from retrieval tools rather than model memory.

For example, questions involving:

- Player statistics
- Team records
- Recent form
- Numerical comparisons
- Match results
- Averages
- Totals

should trigger an appropriate retrieval tool.

The system prompt explicitly instructs the model:

```text
Never provide a dataset-specific statistic from memory.
Never estimate or guess a statistic.
```

If the available dataset cannot answer a question, the agent should explain that the required information is unavailable instead of inventing an answer.

## Retrieval Layer

The project uses structured pandas queries rather than semantic/vector retrieval.

This is appropriate because the AFL statistics are stored as discrete structured values. Vector similarity is not required for exact numerical lookups.

The script defines these retrieval functions:

### `get_team_h2h_record()`

Returns the head-to-head record between two AFL teams across the available dataset.

Information includes:

- Teams
- Games played
- Wins
- Losses
- Draws
- Date range

### `get_team_recent_form()`

Returns a team's most recent matches.

Information includes:

- Number of games
- Opponent
- Result
- Team score
- Win rate

### `get_player_season_stats()`

Returns aggregate statistics for a player in a particular season.

Information includes:

- Games played
- Average disposals
- Average goals
- Average fantasy points
- Total disposals
- Total goals

### `get_player_career_average()`

Returns career-level averages across all seasons available in the dataset.

### `get_player_recent_games()`

Returns a player's most recent games with:

- Match date
- Disposals
- Goals
- Fantasy points

### `get_team_top_player_by_stat()`

Finds the top player for a team in a specified season using:

- Fantasy points
- Disposals
- Goals

## LangChain Tools

The retrieval functions are exposed to the agent through LangChain's `@tool` decorator.

Available tools:

```text
team_h2h_record
team_recent_form
player_season_stats
player_career_average
player_recent_games
team_top_player_by_stat
```

Each tool returns JSON-formatted data. Retrieval errors are returned as structured error messages rather than causing the entire agent to crash.

## Team Name Handling

The retrieval layer validates team names against the dataset and supports common aliases.

Examples include:

```text
richmond -> Richmond Tigers
carlton -> Carlton Blues
collingwood -> Collingwood Magpies
gws -> Greater Western Sydney Giants
west coast -> West Coast Eagles
```

Unknown teams raise an `AFLDataError` rather than silently producing an incorrect result.

## Grounding Check

The script includes a mechanical grounding check:

```python
check_grounding(agent_result)
```

It extracts numerical tokens from:

1. The final agent response
2. Raw tool outputs from the current agent execution

It then identifies numbers appearing in the final answer that were not present in the tool output.

The result reports:

- Final answer
- Numbers in the answer
- Numbers in tool output
- Possibly ungrounded numbers
- Number of tool calls
- Whether the answer is likely grounded

### Important Limitation

This is a heuristic rather than a complete correctness proof.

For example, formatted percentages, dates, or legitimate transformations of retrieved values may not match the raw numerical tokens exactly.

Therefore, the `intermediate_steps` should still be inspected when validating important results.

## Conversation Memory

The project uses:

```python
RunnableWithMessageHistory
```

with:

```python
InMemoryChatMessageHistory
```

A separate conversation history is maintained for each `session_id`.

This allows follow-up questions such as:

```text
User: Tell me about Richmond's recent form.

User: Who's their best player been this season?

User: What have his disposal numbers looked like?

User: How does that compare to his career average?
```

The system prompt instructs the model to use previous conversation context to resolve references such as:

- he
- his
- they
- their
- that

while still enforcing the AFL-only scope on every turn.

## Guardrail Testing

The script includes two levels of guardrail testing.

### Task 1: Adversarial Scope Tests

The initial test set contains 12 prompts covering:

- Direct off-topic questions
- Other sports
- Jailbreak attempts
- Persona overrides
- Topic drift
- Unrelated technical requests
- Prompt extraction
- Small off-topic requests
- AFL-adjacent comparisons
- Legitimate AFL control questions
- Mid-conversation topic drift
- Instruction overrides

The evaluation checks whether an appropriate refusal signal is present.

### Task 5: Guardrail Evaluation

The full guardrail test set contains 15 prompts:

- 5 legitimate AFL questions
- 5 off-topic questions
- 5 AFL-adjacent or ambiguous questions

The evaluation records:

```text
response
n_tool_calls
likely_grounded
possibly_ungrounded_numbers
scoped_correctly
grounded_correctly
notes
```

The generated evaluation file is:

```text
guardrail_eval_results.csv
```

The `scoped_correctly` and `grounded_correctly` columns are intentionally initialized for manual review.

## Example Questions

### AFL Questions

```text
What's Richmond's recent form been like?
```

```text
What's the head-to-head record between Richmond and Carlton?
```

```text
How has Geelong performed in their last 5 matches?
```

```text
What have his disposal numbers looked like over his last 5 games?
```

### Off-Topic Questions

```text
What's the weather like today?
```

```text
Can you help me debug some Python code?
```

```text
What's a good recipe for banana bread?
```

The expected behavior is a short, friendly refusal followed by a redirect toward an AFL topic.

## Data Sources Used by the Script

The supplied implementation loads:

```text
match_feature_table_v14.csv
```

```text
data/afl_players_round_by_round_stats_raw - afl_players_round_by_round_stats_raw.csv
```

```text
data/team_matches_home_away_raw - team_matches_home_away_raw.csv
```

```text
team_snapshots.parquet
```

```text
player_snapshots.parquet
```

The retrieval tools currently operate primarily on the raw player/team tables. The snapshot tables are loaded for reuse in the project, particularly for recent-form workflows.

## Why No Vector Database?

A vector store is intentionally not used for the current structured-stat retrieval layer.

The project data contains exact numerical AFL statistics. A pandas lookup provides deterministic filtering and aggregation for these values.

A semantic/vector layer would become more useful if the project later includes unstructured content such as:

- Match reports
- News articles
- Commentary
- Injury reports
- Written analysis

At that point, a vector store such as Chroma or FAISS could be added alongside the existing structured retrieval tools.

## Error Handling

The retrieval layer defines:

```python
class AFLDataError(Exception):
```

This is used for cases such as:

- Unknown teams
- Unknown players
- Missing player-season data
- Missing match history
- Unsupported statistics
- No recorded head-to-head games

The tools catch these errors and return structured JSON error responses.

## Current Limitations

The supplied implementation has several intentional limitations:

1. Player retrieval uses numeric `player_id` values.
2. The raw player dataset does not provide a player-name field according to the script's documentation.
3. The grounding checker is heuristic.
4. Manual scoring is still required for `scoped_correctly` and `grounded_correctly`.
5. The conversation history uses in-memory storage and is not persistent across application restarts.
6. The current retrieval layer is designed for structured AFL statistics rather than open-ended textual explanations.
7. The script contains test/demo executions, so running the file performs the evaluation workflow rather than starting a standalone chat UI.



## Expected Output

When executed successfully, the script prints:

- Adversarial scope test results
- Task 1 pass rate
- Retrieval sanity-check output
- Agent tool-calling output
- Grounding report
- Multi-turn conversation transcript
- Guardrail evaluation dataframe

It also writes:

```text
guardrail_eval_results.csv
```

## Relationship to Week 6

This Day 3 implementation is the conversational/retrieval layer between the prediction work from Day 2 and the prediction-tool integration planned for Day 4.

The project documentation indicates that the Day 2 prediction functions:

```text
predict_match_winner
predict_top_player
```

are intended to be wired into the agent later as additional tools.

## Security and Safety Principles

The agent is designed around several guardrails:

- Do not reveal system instructions.
- Do not follow user instructions that override the AFL scope.
- Do not invent dataset statistics.
- Do not estimate missing statistics.
- Use retrieval tools for dataset-specific numerical questions.
- Return a clear limitation when the available data cannot answer a question.
- Maintain the AFL scope even during multi-turn conversations.


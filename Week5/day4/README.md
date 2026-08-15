 # CrewAI Multi-Agent Collaboration

## CrewAI (Multi-Agent Collaboration, Roles & Task Delegation)

This project explores **multi-agent collaboration using CrewAI** by comparing a specialized multi-agent workflow with a single-agent LangGraph baseline.

The selected business scenario is:

> **Research a competitor, extract business insights, and draft a stakeholder-ready marketing angle.**

The experiment compares:

1. **Single-Agent LangGraph**
2. **Sequential CrewAI**
3. **Hierarchical CrewAI**

The goal is to understand when specialized agents provide value and when the additional orchestration cost is not justified.

---

#  Project Objective

The objectives of this experiment are to:

- Design a multi-agent system with specialized roles.
- Assign role-appropriate tools to agents.
- Configure individual LLMs for each agent.
- Define CrewAI tasks and dependencies.
- Execute a sequential CrewAI workflow.
- Implement hierarchical delegation with a manager agent.
- Compare Sequential and Hierarchical CrewAI.
- Compare both multi-agent approaches with a Single-Agent LangGraph solution.
- Evaluate output quality, latency, token usage, and estimated cost.
- Determine which architecture is most appropriate for the selected business task.

---

#  Business Scenario

## Competitor Research and Marketing Positioning

The selected business problem is:

> **Research a competitor, summarize competitive insights, and develop a stakeholder-ready marketing angle.**

The competitor used in this experiment is **Notion**.

The workflow is:

```text
Notion
   │
   ▼
Market Research
   │
   ▼
Business Insights
   │
   ▼
Marketing Angle
````

The system researches:

* Products
* Pricing
* Features
* Recent marketing activity
* Competitive strengths
* Potential positioning opportunities

The research findings are then analyzed and converted into a concise marketing angle.

---

#  Multi-Agent Design

The CrewAI implementation contains three specialized agents.

## 1 Market Research Analyst

### Role

`Market Research Analyst`

### Goal

Gather accurate, current, source-backed information about the competitor's products, pricing, and recent marketing activity.

### Backstory

The researcher is a meticulous market researcher with experience tracking SaaS competitors. The agent focuses on verifiable facts, validates dates, prefers primary sources, and avoids inventing dates, prices, products, campaigns, or claims.

### Responsibilities

* Search the web for competitor information.
* Prefer official and primary sources.
* Verify publication dates.
* Identify current pricing and product information.
* Collect evidence and source URLs.
* Avoid unsupported claims.

### Tool

**Tavily Search Tool**

The researcher is assigned the Tavily search tool because external information retrieval is its primary responsibility.

---

## 2 Business Insights Analyst

### Role

`Business Insights Analyst`

### Goal

Transform the research findings into 3–5 prioritized, evidence-based business insights.

### Backstory

The analyst is a strategic competitive-intelligence specialist who identifies business implications from verified evidence while distinguishing demonstrated strengths, weaknesses, and potential opportunities.

### Responsibilities

* Review the research output.
* Identify competitive strengths and weaknesses.
* Extract 3–5 prioritized insights.
* Distinguish evidence from assumptions.
* Identify relevant positioning opportunities.

### Tools

**None**

The analyst does not need direct web access because the researcher has already collected the required evidence.

This keeps responsibilities separated and avoids duplicate searches and unnecessary model usage.

---

## 3 Marketing Content Strategist

### Role

`Marketing Content Strategist`

### Goal

Convert validated business insights into a concise, stakeholder-ready marketing angle.

### Backstory

The copywriter is a careful B2B marketing strategist who creates concise, evidence-based positioning while avoiding unsupported claims about the company's capabilities.

### Responsibilities

* Use the analyst's findings.
* Produce one marketing headline.
* Produce three supporting marketing points.
* Reference the relevant insights.
* Maintain an appropriate professional tone.
* Avoid inventing unsupported capabilities or advantages.

### Tools

**None**

The copywriter works from the validated analyst output and therefore does not require independent web search.

---

#  Why Multiple Specialized Agents?

A specialized multi-agent architecture can outperform a generalist agent when a problem naturally separates into distinct stages.

For this task, research, analysis, and marketing generation require different objectives and prompting strategies. Separating these responsibilities provides specialization and can improve the quality of the final output.

However, multi-agent systems introduce additional model calls, token usage, latency, coordination overhead, and debugging complexity.

For relatively simple or linear workflows, a well-designed single-agent system can therefore be more efficient.

---

#  Agent LLM Configuration

Each agent has its own LLM configuration.

| Agent                        | Model                      | Temperature |
| ---------------------------- | -------------------------- | ----------: |
| Market Research Analyst      | GPT-4o-mini via OpenRouter |         0.2 |
| Business Insights Analyst    | GPT-4o-mini via OpenRouter |         0.3 |
| Marketing Content Strategist | GPT-4o-mini via OpenRouter |         0.7 |

The temperatures were selected according to the type of work:

* **Research:** lower temperature for factual consistency.
* **Analysis:** moderate temperature for interpretation.
* **Marketing:** higher temperature for controlled creativity.

---

#  Tool Assignment

The tool access is intentionally **role-specific**.

| Agent      | Tool          | Justification                                                                   |
| ---------- | ------------- | ------------------------------------------------------------------------------- |
| Researcher | Tavily Search | Requires current external information and source verification.                  |
| Analyst    | None          | Works from the researcher's evidence and focuses on synthesis.                  |
| Copywriter | None          | Converts validated insights into marketing content without additional research. |

Not every agent receives every tool.

This design avoids:

* Duplicate web searches
* Unnecessary token usage
* Increased latency
* Overlapping responsibilities
* Reduced separation of concerns

The responsibility flow is:

```text
Researcher → retrieves evidence
      ↓
Analyst → interprets evidence
      ↓
Copywriter → communicates insights
```

---

#  Task Design

The CrewAI workflow contains three primary tasks.

## Task 1 — Competitor Research

The researcher gathers current, source-backed information about Notion.

The expected output contains structured findings such as:

* Finding
* Evidence
* Publication date
* Source
* URL
* Competitive relevance

The output is passed to the Business Insights Analyst.

---

## Task 2 — Business Analysis

The analyst receives the research output as context.

The expected output contains:

* 3–5 prioritized insights
* Competitive strengths
* Competitive weaknesses
* Potential opportunities
* Evidence supporting each insight

The analyst must use only information supported by the research.

---

## Task 3 — Marketing Angle

The copywriter receives the analyst's insights as context.

The expected output contains:

* One marketing headline
* Three supporting marketing points
* References to the relevant insights

The copywriter is instructed not to invent unsupported product capabilities, prices, or advantages.

---

#  Sequential CrewAI

The Sequential CrewAI workflow is:

```text
Researcher
    ↓
Analyst
    ↓
Copywriter
```

The crew uses:

```python
Process.sequential
```

The workflow is deterministic in structure:

1. Research is performed.
2. Research findings are passed to the analyst.
3. The analyst produces insights.
4. Insights are passed to the copywriter.
5. The copywriter produces the final marketing angle.

This architecture is appropriate because the workflow has a known order and explicit dependencies.

---

#  Output Formatting Issue and Fix

During the experiment, a formatting issue was identified where the output of an upstream task was not sufficiently structured for downstream processing.

The issue was addressed by making the expected output more explicit.

The prompts were updated to require:

* Structured findings
* Consistent insight numbering
* Clear evidence
* Explicit source references
* Stable output sections

The marketing task was then instructed to reference the analyst's numbered insights.

This improved the compatibility between upstream and downstream tasks.

---

#  Hierarchical CrewAI

A second version of the crew was implemented using:

```python
Process.hierarchical
```

The hierarchical workflow introduces a manager agent.

Conceptually:

```text
                    Manager
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
     Researcher     Analyst     Copywriter
```

The manager is responsible for coordinating and reviewing the work of the specialized agents.

Unlike the sequential architecture, hierarchical execution can dynamically delegate work and review intermediate results.

---

# Sequential vs. Hierarchical

| Architecture     | Pros                                                                                    | Cons                                                                                                    | Best Used When                                                                     |
| ---------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| **Sequential**   | Predictable order; clear dependencies; easy debugging; lower latency than hierarchical. | Less flexible; fixed workflow; limited dynamic delegation.                                              | The task naturally follows a known sequence such as research → analysis → writing. |
| **Hierarchical** | Manager can delegate, coordinate, review, and adapt work dynamically.                   | Higher latency and coordination overhead; more model usage; can reduce reliability on simple workflows. | The task is complex, open-ended, or requires dynamic delegation and review.        |

---

#  Single-Agent Architecture

The project also compares the CrewAI implementations with a **Single-Agent LangGraph** solution developed previously.

The Single-Agent architecture uses one agent to perform the overall workflow instead of separating research, analysis, and writing across multiple specialized agents.

Conceptually:

```text
Single Agent
     │
     ├── Research
     ├── Analysis
     └── Marketing Output
```

The purpose of this comparison is to determine whether specialization provides enough additional quality to justify the extra model calls and orchestration overhead.

---

#  Evaluation Criteria

Three primary success criteria were used.

## 1. Factual Grounding

The output should be based on available research and avoid unsupported claims.

## 2. Completeness

The output should address the required competitor information and produce the requested business insights.

## 3. Marketing Quality and Tone

The final output should be:

* Concise
* Professional
* Stakeholder-ready
* Useful for marketing positioning
* Consistent with the available evidence

---

#  Experimental Evaluation

Three runs were performed for the CrewAI architectures.

The systems were evaluated using:

1. Quality
2. Token usage
3. Estimated cost
4. Latency
5. Reliability and consistency

The comparison also includes the previously measured Single-Agent LangGraph baseline.

---

#  Performance Results

The measured averages were:

| Architecture               | Avg Quality | Avg Total Tokens | Avg Estimated Cost | Avg Latency |
| -------------------------- | ----------: | ---------------: | -----------------: | ----------: |
| **Single-Agent LangGraph** |     11.0/15 |           ~3,615 |          ~$0.00076 |    ~10.49 s |
| **Sequential CrewAI**      | **12.0/15** |        64,484.67 |          $0.012420 |     18.45 s |
| **Hierarchical CrewAI**    |      9.3/15 |        61,431.00 |          $0.012613 |     46.23 s |

---

#  Quality Comparison

## Single-Agent LangGraph

The Single-Agent solution achieved:

**11.0/15**

It produced competitive results while using substantially fewer tokens and less execution time.

---

## Sequential CrewAI

The Sequential CrewAI solution achieved:

**12.0/15**

This was the highest quality score among the evaluated architectures.

The separation between:

```text
Research → Analysis → Marketing
```

was beneficial for this workflow.

---

## Hierarchical CrewAI

The Hierarchical CrewAI solution achieved:

**9.3/15**

The manager and delegation layer did not produce a corresponding quality improvement.

For this particular task, the additional coordination overhead was not justified.

---

#  Cost Comparison

| Architecture           | Avg Total Tokens | Avg Estimated Cost |
| ---------------------- | ---------------: | -----------------: |
| Single-Agent LangGraph |           ~3,615 |          ~$0.00076 |
| Sequential CrewAI      |        64,484.67 |          $0.012420 |
| Hierarchical CrewAI    |        61,431.00 |          $0.012613 |

The Single-Agent architecture was substantially more cost-efficient.

The multi-agent approaches used approximately **17–18× more total tokens** than the Single-Agent baseline.

Although Hierarchical CrewAI used fewer total tokens than Sequential CrewAI, its estimated cost was slightly higher because it generated more completion tokens.

Therefore:

> **Total token count is not the only factor that determines monetary cost.**

Actual monetary cost depends on the provider's input and output token pricing.

---

#  Latency Comparison

| Architecture           | Average Latency |
| ---------------------- | --------------: |
| Single-Agent LangGraph |        ~10.49 s |
| Sequential CrewAI      |         18.45 s |
| Hierarchical CrewAI    |         46.23 s |

The Single-Agent solution was the fastest.

Sequential CrewAI introduced additional model calls but remained considerably faster than the hierarchical implementation.

Hierarchical CrewAI had the highest latency because of the additional manager and delegation coordination.

---

#  Manual Quality Evaluation

The manual evaluation used a maximum score of **15 points**.

The quality dimensions were based on:

* Factual grounding
* Completeness
* Marketing quality/tone

The observed average scores were:

| Architecture           | Average Quality |
| ---------------------- | --------------: |
| Single-Agent LangGraph |         11.0/15 |
| Sequential CrewAI      |     **12.0/15** |
| Hierarchical CrewAI    |          9.3/15 |

The Sequential CrewAI architecture produced the highest average manual quality score.

The Hierarchical architecture did not provide a quality improvement for this specific workflow.

---

#  Was the Multi-Agent Crew Worth It?

For this specific Notion competitor-research task, the **Sequential CrewAI** approach produced the best quality score and was the strongest multi-agent architecture.

However, the quality improvement from **11.0/15 to 12.0/15** was relatively small compared with the increase from approximately **3,615 tokens to 64,485 tokens**.

The **Hierarchical CrewAI** approach was not worth the additional complexity for this workflow because it produced a lower quality score of **9.3/15** while also having the highest latency.

Therefore, a well-designed Single-Agent solution is the most cost-efficient option, while Sequential CrewAI is justified when the benefits of specialization are important enough to justify the additional cost and latency.

---

#  When to Use Each Architecture

## Use Single-Agent LangGraph When

* The task is relatively simple.
* Low cost is important.
* Low latency is important.
* The workflow does not require strong specialization.
* Simplicity and maintainability are priorities.

## Use Sequential CrewAI When

* The workflow has clearly defined stages.
* Each stage has a distinct responsibility.
* Later stages depend on earlier outputs.
* Specialization can improve quality.
* The additional cost is acceptable.

## Use Hierarchical CrewAI When

* The workflow is complex.
* Dynamic delegation is required.
* A manager needs to coordinate multiple specialists.
* Intermediate results require review.
* The workflow cannot be represented effectively as a fixed sequence.

---

#  Final Recommendation

For the selected competitor-research workflow:

### Best for efficiency

**Single-Agent LangGraph**

It provides the lowest token usage, lowest estimated cost, and lowest latency.

### Best multi-agent architecture

**Sequential CrewAI**

It achieved the highest quality score while maintaining substantially lower latency than the hierarchical implementation.

### Best for complex dynamic workflows

**Hierarchical CrewAI**

Although it did not perform best in this experiment, it is useful when dynamic delegation and manager-level coordination are genuinely required.

---

#  Final Conclusion

This experiment demonstrates that there is no universally best agent architecture.

For the selected Notion competitor-research workflow:

* **Single-Agent LangGraph** was the most efficient in terms of tokens, cost, and latency.
* **Sequential CrewAI** achieved the highest quality and was the strongest multi-agent architecture.
* **Hierarchical CrewAI** added dynamic delegation but introduced significant coordination overhead without improving quality.

Overall:

> **Sequential CrewAI is the preferred multi-agent architecture for this specific task, while Single-Agent LangGraph is the preferred architecture when cost, latency, and simplicity are the primary objectives.**

Hierarchical CrewAI should be reserved for workflows where dynamic delegation and manager-level coordination provide enough value to justify the additional overhead.

---

#  Project Structure

```text
week5/day4/
│
├── CrewAI.ipynb
├── README.md
├── CrewAI_Comparison_Report.pdf
│
└── outputs/
    └── execution_logs/
```

---

# Technologies Used

* Python
* CrewAI
* LangGraph
* OpenRouter
* GPT-4o-mini
* Tavily Search
* Pydantic
* Jupyter Notebook / Google Colab

---

#  Key Takeaway

The main lesson from this experiment is:

> **More agents do not automatically mean a better system.**

Multi-agent architecture is valuable when specialization, delegation, or coordination solves a problem that a single agent handles poorly.

For well-defined workflows, a sequential multi-agent design can provide useful specialization.

For complex dynamic workflows, hierarchical delegation can become valuable.

However, when efficiency is the primary objective, a carefully designed single-agent system can be significantly cheaper and faster.

---

## Author

**Saira Fatima**




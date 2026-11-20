from prometheus_client import Counter, Histogram


# Agent Execution Metrics

AGENT_EXECUTIONS = Counter(
    "agent_executions_total",
    "Total number of agent executions",
    ["status"],
)

AGENT_EXECUTION_DURATION = Histogram(
    "agent_execution_duration_seconds",
    "Total duration of agent executions",
    buckets=(0.1, 0.5, 1, 2, 5, 10, 20, 30, 60),
)

AGENT_ITERATIONS = Histogram(
    "agent_iterations",
    "Number of iterations per agent execution",
    buckets=(1, 2, 3, 4, 5, 7, 10),
)



# Agent Tool Metrics

AGENT_TOOL_CALLS = Counter(
    "agent_tool_calls_total",
    "Total number of agent tool calls",
    ["tool_name", "status"],
)

AGENT_TOOL_DURATION = Histogram(
    "agent_tool_duration_seconds",
    "Duration of agent tool executions",
    ["tool_name"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10, 30),
)


# Agent LLM Metrics

AGENT_LLM_CALLS = Counter(
    "agent_llm_calls_total",
    "Total number of LLM calls made by the agent",
    ["provider", "status"],
)

AGENT_LLM_DURATION = Histogram(
    "agent_llm_duration_seconds",
    "Duration of agent LLM calls",
    ["provider"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 20, 30),
)

AGENT_LLM_TOKENS = Counter(
    "agent_llm_tokens_total",
    "Total tokens consumed by agent LLM calls",
    ["provider", "token_type"],
)

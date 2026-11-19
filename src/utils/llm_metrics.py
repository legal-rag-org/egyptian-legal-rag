from prometheus_client import Counter, Histogram

# Number of executions per provider.
# One execution may contain multiple retry attempts 
LLM_PROVIDER_CALLS = Counter(
    "llm_provider_calls_total",
    "Total LLM provider executions",
    ["provider", "operation", "outcome"],
)

# Time spent executing an operation on a provider
# Including its retries
LLM_PROVIDER_DURATION = Histogram(
    "llm_provider_duration_seconds",
    "LLM provider execution duration",
    ["provider", "operation"],
)


# Number of retries actually performed
LLM_RETRIES = Counter(
    "llm_retries_total",
    "Total LLM retry attempts",
    ["provider", "error_type"],
)

# Number of transitions from the primary provider to a fallback.
LLM_FALLBACKS = Counter(
    "llm_fallbacks_total",
    "Total LLM fallback transitions",
    ["primary_provider", "fallback_provider", "operation"],
)
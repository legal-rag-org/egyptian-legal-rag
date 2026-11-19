from dataclasses import dataclass, field


@dataclass
class RetryConfig:
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 10.0
    exponential_base: float = 2.0


@dataclass
class ResilienceConfig:
    timeout: float = 30.0
    retry: RetryConfig = field(default_factory=RetryConfig)
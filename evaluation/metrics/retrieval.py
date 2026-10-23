import math


def is_relevant(score: int, threshold: int = 1) -> bool:
    return score >= threshold


def precision_at_k(scores: list[int], k: int, threshold: int = 1) -> float:
    top = scores[:k]
    if not top:
        return 0.0
    return sum(is_relevant(s, threshold) for s in top) / k


def hit_at_k(scores: list[int], k: int, threshold: int = 1) -> int:
    return int(any(is_relevant(s, threshold) for s in scores[:k]))


def reciprocal_rank(scores: list[int], threshold: int = 1) -> float:
    for rank, s in enumerate(scores, start=1):
        if is_relevant(s, threshold):
            return 1 / rank
    return 0.0


def dcg(scores: list[int]) -> float:
    return sum(s / math.log2(i + 1) for i, s in enumerate(scores, start=1))


def ndcg_at_k(scores: list[int], k: int) -> float:
    top = scores[:k]
    ideal = dcg(sorted(top, reverse=True))
    return dcg(top) / ideal if ideal > 0 else 0.0

def context_recall(supported: list[bool]) -> float | None:
    if not supported:
        return None
    return sum(supported) / len(supported)
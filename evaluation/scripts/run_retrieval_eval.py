import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from evaluation.judges.recall_judge import judge_recall
from evaluation.metrics.retrieval import context_recall

from evaluation.judges.retrieval_judge import JUDGE_MODEL, judge_chunk
from evaluation.metrics.retrieval import (
    hit_at_k,
    ndcg_at_k,
    precision_at_k,
    reciprocal_rank,
)
from evaluation.scripts.retriever_client import retrieve

DATASET = Path("evaluation/datasets/labour_dataset.json")
RESULTS_DIR = Path("evaluation/results")


async def judge_one(sem: asyncio.Semaphore, question: str, chunk: str) -> dict:
    async with sem:
        try:
            j = await asyncio.to_thread(judge_chunk, question, chunk)
            return {"score": j.score, "reasoning": j.reasoning}
        except Exception as e:
            return {"score": None, "reasoning": f"JUDGE_FAILED: {e}"}


async def eval_question(sem, item: dict, project_id: int, k: int) -> dict:
    question = item["question"]
    ground_truth = item.get("ground_truth")
    chunks = await retrieve(question, project_id, k)

    judgments = await asyncio.gather(
        *[judge_one(sem, question, c["text"]) for c in chunks]
    )

    record = {
        "question": question,
        "ground_truth": ground_truth,
        "retrieved": [
            {
                "rank": i,
                "text": c["text"],
                "source": c.get("source"),
                "page": c.get("page"),
                "retriever_score": c.get("score"),
                **j,
            }
            for i, (c, j) in enumerate(zip(chunks, judgments), start=1)
        ],
    }

    scores = [r["score"] for r in record["retrieved"]]
    if any(s is None for s in scores):
        record["failed"] = True
        return record

    record["failed"] = False
    record["metrics"] = {
        "precision@k": precision_at_k(scores, k),
        "precision@k_strict": precision_at_k(scores, k, threshold=2),
        "hit@k": hit_at_k(scores, k),
        "rr": reciprocal_rank(scores),
        "ndcg@k": ndcg_at_k(scores, k),
    }

    # Context Recall needs ground truth
    if ground_truth:
        if not chunks:
            record["metrics"]["context_recall"] = 0.0
            record["recall_claims"] = []
        else:
            try:
                async with sem:
                    claims = await asyncio.to_thread(
                        judge_recall, ground_truth, [c["text"] for c in chunks]
                    )
                record["recall_claims"] = claims
                record["metrics"]["context_recall"] = context_recall(
                    [c["supported"] for c in claims]
                )
                record["metrics"]["context_recall_verified"] = context_recall(
                    [c["supported"] and c["evidence_found"] for c in claims]
                )
            except Exception as e:
                record["recall_error"] = str(e)
    return record


def aggregate(records: list[dict]) -> dict:
    ok = [r for r in records if not r["failed"]]
    if not ok:
        return {}
    keys = {k for r in ok for k in r["metrics"]}
    agg = {}
    for key in sorted(keys):
        vals = [r["metrics"][key] for r in ok if r["metrics"].get(key) is not None]
        agg[key] = round(sum(vals) / len(vals), 3)
    agg["n_questions"] = len(ok)
    agg["n_failed"] = len(records) - len(ok)
    return agg

async def main(project_id: int, k: int, limit: int | None, concurrency: int):
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    if limit:
        data = data[:limit]

    sem = asyncio.Semaphore(concurrency)
    records = []
    for i, item in enumerate(data, start=1):
        rec = await eval_question(sem, item, project_id, k)
        records.append(rec)
        status = "FAILED" if rec["failed"] else [r["score"] for r in rec["retrieved"]]
        print(f"[{i}/{len(data)}] {status} | {item['question'][:50]}")

    summary = aggregate(records)
    print("\n Summary")
    for key, val in summary.items():
        print(f"{key}: {val}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"vector_keyword_rewritten_query{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(
        json.dumps(
            {
                "config": {"judge_model": JUDGE_MODEL, "k": k, "project_id": project_id},
                "summary": summary,
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--project-id", type=int, default=1)
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--concurrency", type=int, default=3)
    a = p.parse_args()
    asyncio.run(main(a.project_id, a.k, a.limit, a.concurrency))
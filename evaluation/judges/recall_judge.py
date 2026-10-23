import json
import re
import unicodedata

from pydantic import BaseModel

from evaluation.judges.retrieval_judge import JUDGE_MODEL, client


class ClaimCheck(BaseModel):
    claim: str
    supported: bool
    evidence: str


class RecallResult(BaseModel):
    claims: list[ClaimCheck]


RECALL_PROMPT = """You are a strict fact-checker for a retrieval system over Egyptian legal documents.

Step 1: Break the reference answer into atomic claims.
Step 2: For each claim, decide whether the retrieved contexts ALONE contain the information to support it.

Rules:
- Do NOT use your own knowledge, even if the claim is true in reality.
- A claim is supported only if a context states it explicitly or it follows directly from the text.
- Each claim must contain ONE fact. If the reference lists several items, create one claim per item.
- If a claim contains several items, it is supported ONLY if ALL of them appear in the contexts. If any item is missing, supported must be false.
- "evidence" must be copied CHARACTER-FOR-CHARACTER from the contexts, including odd spacing or broken letters. Do NOT fix spelling or spaces. Use "none" if the claim is not supported.
- Write the claims in the same language as the reference answer.

Reference answer:
{ground_truth}

Retrieved contexts:
{contexts}

Respond with ONLY a JSON object in this format:
{{"claims": [{{"claim": "...", "supported": true, "evidence": "..."}}]}}
"""

_MARKS = re.compile(r"[\u064B-\u0652\u0670\u0640]")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def _loose(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = _MARKS.sub("", text)
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ى", "ي"), ("ة", "ه")):
        text = text.replace(a, b)
    return re.sub(r"[\W_]+", "", text)


def _parse(raw: str) -> RecallResult:
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    return RecallResult.model_validate(json.loads(match.group(0) if match else raw))


def judge_recall(ground_truth: str, chunks: list[str], retries: int = 3) -> list[dict]:
    contexts = "\n\n".join(
        f"[Context {i}]\n{_norm(c)}" for i, c in enumerate(chunks, start=1)
    )
    loose_ctx = _loose(contexts)
    last_err = None
    for _ in range(retries):
        try:
            response = client.chat.completions.create(
                model=JUDGE_MODEL,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[{
                    "role": "user",
                    "content": RECALL_PROMPT.format(
                        ground_truth=ground_truth, contexts=contexts
                    ),
                }],
            )
            result = _parse(response.choices[0].message.content)
            if not result.claims:
                raise ValueError("no claims returned")
            out = []
            for c in result.claims:
                ev = _loose(c.evidence)
                out.append({
                    **c.model_dump(),
                    "evidence_found": len(ev) >= 15 and ev in loose_ctx,
                })
            return out
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Recall judge failed after {retries} tries: {last_err}")
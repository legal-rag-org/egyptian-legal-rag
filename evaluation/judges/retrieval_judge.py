import json
from typing import Literal

import unicodedata 

from openai import OpenAI
from pydantic import BaseModel, Field

from evaluation.config import settings

import re


class RelevanceJudgment(BaseModel):
    reasoning: str = Field(description="Short explanation (1-2 sentences) before the score")
    score: Literal[0, 1, 2]



JUDGE_PROMPT = """You are an impartial evaluator for a retrieval
system over Egyptian legal documents.

Given a question and a retrieved passage, rate how useful the
passage is for answering the question.

Scale:
0 = irrelevant.
1 = partially relevant, but missing key details.
2 = highly relevant, contains the answer or key evidence.

Rules:
- Judge ONLY from the passage text.
- Do not use your own legal knowledge.
- Mentioning a topic without the needed rule or condition is 1.
- Passage length is not a quality signal.

Question: {question}

Passage:
{chunk}

Respond with ONLY a JSON object with exactly these keys, in this order:
{{"reasoning": "<1-2 sentences>", "score": <0, 1, or 2>}}
"""


JUDGE_MODEL = "qwen2.5:7b-instruct-q4_0"

client = OpenAI(
    api_key="ollama",
    base_url=settings.OPENAI_API_URL,
)

def _parse(raw: str) -> RelevanceJudgment:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    return RelevanceJudgment.model_validate(json.loads(match.group(0) if match else raw))


def judge_chunk(question: str, chunk: str, retries: int = 3) -> RelevanceJudgment:
    chunk = unicodedata.normalize("NFKC", chunk) 
    last_err = None
    for _ in range(retries):
        try:
            response = client.chat.completions.create(
                model=JUDGE_MODEL,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": JUDGE_PROMPT.format(question=question, chunk=chunk)}],
            )
            return _parse(response.choices[0].message.content)
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Judge failed after {retries} tries: {last_err}")
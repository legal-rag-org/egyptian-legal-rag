import httpx

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1/nlp"    

async def retrieve(question: str, project_id: int, k: int = 5) -> list[dict]:
    url = f"{BASE_URL}{API_PREFIX}/index/search/{project_id}"
    payload = {"text": question, "reranker_limit": k}

    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(url, json=payload)

    if resp.status_code == 400:
        return []
    resp.raise_for_status()
    return resp.json()["results"]
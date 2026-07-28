"""RAG service for the IRCC knowledge-base chatbot.

Pipeline:
  1. Ingestion   - semantic chunking + embedding of source documents
  2. Retrieval   - hybrid search (vector cosine + keyword overlap) with rerank
  3. Generation  - Claude answer grounded in retrieved chunks, with citations

Every external dependency degrades gracefully:
  - No Voyage key  -> deterministic local embedding (hashing) so retrieval works
  - No Anthropic key -> extractive fallback answer built from top chunks
This keeps the whole workflow usable offline and in tests.
"""

import hashlib
import math
import re
from typing import Any

import httpx

from app.core.config import settings

# Chunking parameters (character-based, approximate token budget).
CHUNK_TARGET_CHARS = 900
CHUNK_OVERLAP_CHARS = 150
MIN_CHUNK_CHARS = 40


def content_hash(text: str) -> str:
    """Stable hash of source content for change detection."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9À-ſ]+", text.lower())


class RagService:
    def __init__(self):
        self._voyage_key = settings.voyage_api_key
        self._embedding_model = settings.embedding_model
        self._dim = settings.embedding_dim
        self._anthropic_key = settings.anthropic_api_key
        self._chat_model = "claude-sonnet-4-20250514"

    # ------------------------------------------------------------------ #
    # Capability flags
    # ------------------------------------------------------------------ #
    @property
    def embedding_available(self) -> bool:
        return bool(self._voyage_key)

    @property
    def generation_available(self) -> bool:
        return bool(self._anthropic_key)

    # ------------------------------------------------------------------ #
    # Chunking
    # ------------------------------------------------------------------ #
    def chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping semantic chunks on paragraph boundaries."""
        text = text.strip()
        if not text:
            return []

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks: list[str] = []
        current = ""

        for para in paragraphs:
            if not current:
                current = para
            elif len(current) + len(para) + 2 <= CHUNK_TARGET_CHARS:
                current = f"{current}\n\n{para}"
            else:
                chunks.append(current)
                # Carry a tail overlap for context continuity.
                tail = current[-CHUNK_OVERLAP_CHARS:]
                current = f"{tail}\n\n{para}" if len(para) < CHUNK_TARGET_CHARS else para

            # A single oversized paragraph gets hard-split.
            while len(current) > CHUNK_TARGET_CHARS * 1.5:
                chunks.append(current[:CHUNK_TARGET_CHARS])
                current = current[CHUNK_TARGET_CHARS - CHUNK_OVERLAP_CHARS:]

        if current.strip() and len(current.strip()) >= MIN_CHUNK_CHARS:
            chunks.append(current.strip())
        elif current.strip() and chunks:
            chunks[-1] = f"{chunks[-1]}\n\n{current.strip()}"
        elif current.strip():
            chunks.append(current.strip())

        return chunks

    @staticmethod
    def estimate_tokens(text: str) -> int:
        # Rough heuristic: ~4 chars per token.
        return max(1, len(text) // 4)

    # ------------------------------------------------------------------ #
    # Embedding
    # ------------------------------------------------------------------ #
    def _local_embedding(self, text: str) -> list[float]:
        """Deterministic hashing embedding (bag-of-words into fixed dims).

        Not semantically rich, but stable and dependency-free so retrieval and
        tests work without an embedding provider.
        """
        vec = [0.0] * self._dim
        for token in _tokenize(text):
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dim
            sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
            vec[idx] += sign
        return _normalize(vec)

    async def embed(self, text: str) -> list[float]:
        """Embed a single text (Voyage API or local fallback)."""
        result = await self.embed_batch([text])
        return result[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""
        if not texts:
            return []
        if not self.embedding_available:
            return [self._local_embedding(t) for t in texts]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.voyageai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {self._voyage_key}"},
                    json={"input": texts, "model": self._embedding_model},
                )
                response.raise_for_status()
                data = response.json()
                return [_normalize(item["embedding"]) for item in data["data"]]
        except Exception:
            return [self._local_embedding(t) for t in texts]

    # ------------------------------------------------------------------ #
    # Retrieval / ranking
    # ------------------------------------------------------------------ #
    def hybrid_score(
        self, query: str, query_vec: list[float], chunk_vec: list[float], chunk_text: str
    ) -> float:
        """Combine vector cosine similarity with keyword overlap (rerank)."""
        vector = cosine_similarity(query_vec, chunk_vec)
        keyword = self._keyword_overlap(query, chunk_text)
        return 0.75 * vector + 0.25 * keyword

    @staticmethod
    def _keyword_overlap(query: str, text: str) -> float:
        q = set(_tokenize(query))
        if not q:
            return 0.0
        t = set(_tokenize(text))
        if not t:
            return 0.0
        return len(q & t) / len(q)

    def rank_chunks(
        self, query: str, query_vec: list[float], chunks: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Rank chunk dicts ({content, embedding, ...}) by hybrid score."""
        scored = []
        for ch in chunks:
            score = self.hybrid_score(query, query_vec, ch["embedding"], ch["content"])
            scored.append({**ch, "score": round(score, 4)})
        scored.sort(key=lambda c: c["score"], reverse=True)
        return scored[:top_k]

    # ------------------------------------------------------------------ #
    # Generation
    # ------------------------------------------------------------------ #
    async def generate_answer(
        self, question: str, contexts: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate a grounded answer from retrieved contexts."""
        if not contexts:
            return {
                "answer": (
                    "Je n'ai pas trouve d'information pertinente dans la base de "
                    "connaissances pour repondre a cette question."
                ),
                "method": "no_context",
            }

        if self.generation_available:
            try:
                answer = await self._generate_with_ai(question, contexts)
                return {"answer": answer, "method": "ai"}
            except Exception:
                pass

        return {"answer": self._extractive_answer(contexts), "method": "extractive"}

    async def _generate_with_ai(
        self, question: str, contexts: list[dict[str, Any]]
    ) -> str:
        context_block = "\n\n".join(
            f"[Source {i + 1}] {c.get('title', 'Document')}\n{c['content']}"
            for i, c in enumerate(contexts)
        )
        prompt = (
            "Tu es un assistant specialise en immigration canadienne (IRCC). "
            "Reponds a la question en te basant UNIQUEMENT sur les sources fournies. "
            "Cite les sources pertinentes entre crochets, ex: [Source 1]. "
            "Si les sources ne permettent pas de repondre, dis-le clairement. "
            "Ne jamais inventer de procedure ou de delai.\n\n"
            f"Sources:\n{context_block}\n\n"
            f"Question: {question}\n\n"
            "Reponse (en francais, precise et professionnelle):"
        )
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self._anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self._chat_model,
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]

    @staticmethod
    def _extractive_answer(contexts: list[dict[str, Any]]) -> str:
        """Fallback answer: summarize the most relevant chunks with citations."""
        parts = ["D'apres la base de connaissances IRCC:\n"]
        for i, c in enumerate(contexts[:3]):
            snippet = c["content"].strip()
            if len(snippet) > 400:
                snippet = snippet[:400].rsplit(" ", 1)[0] + "..."
            parts.append(f"[Source {i + 1}] {snippet}")
        return "\n\n".join(parts)


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    # Vectors are pre-normalized, so dot == cosine; clamp for float safety.
    return max(-1.0, min(1.0, dot))


# Singleton
rag_service = RagService()

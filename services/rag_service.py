import hashlib
import pickle
from pathlib import Path
from typing import Optional

import faiss
import numpy as np
import pdfplumber
import tiktoken
from openai import OpenAI

from core.config import settings
from core.logging_config import get_logger

logger = get_logger(__name__)

client = OpenAI(api_key=settings.openai_api_key)
tokenizer = tiktoken.get_encoding("cl100k_base")

VECTOR_STORE_PATH = Path(settings.vector_store_dir)
INDEX_FILE = VECTOR_STORE_PATH / "index.faiss"
CHUNKS_FILE = VECTOR_STORE_PATH / "chunks.pkl"
HASH_FILE = VECTOR_STORE_PATH / "source_hash.txt"

_index: Optional[faiss.Index] = None
_chunks: list[dict] = []


def _compute_source_hash() -> str:
    """Hash all source filenames + sizes (PDFs and TXT) to detect any changes."""
    kb_path = Path(settings.knowledge_resources_dir)
    parts = [
        f"{source.name}:{source.stat().st_size}"
        for source in sorted(kb_path.glob("**/*.*"))
        if source.suffix.lower() in {".pdf", ".txt"}
    ]
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def _extract_text_from_sources() -> list[dict]:
    """Extract text from PDFs and plain text files in knowledge_resources/."""
    kb_path = Path(settings.knowledge_resources_dir)
    pages: list[dict] = []

    # Extract from PDFs
    for pdf_path in sorted(kb_path.glob("**/*.pdf")):
        logger.info("Extracting text from PDF: %s", pdf_path.name)
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append({
                        "text": text,
                        "source": pdf_path.name,
                        "page": page_num,
                    })

    # Extract from plain text files
    for txt_path in sorted(kb_path.glob("**/*.txt")):
        logger.info("Extracting text from: %s", txt_path.name)
        text = txt_path.read_text(encoding="utf-8").strip()
        if text:
            pages.append({
                "text": text,
                "source": txt_path.name,
                "page": 1,
            })

    pdf_count = len(list(kb_path.glob("**/*.pdf")))
    txt_count = len(list(kb_path.glob("**/*.txt")))
    logger.info("Extracted %d pages from %d PDFs and %d text files", len(pages), pdf_count, txt_count)
    return pages


def _chunk_text(pages: list[dict]) -> list[dict]:
    """Split pages into overlapping token-sized chunks."""
    chunks: list[dict] = []

    for page in pages:
        tokens = tokenizer.encode(page["text"])
        start = 0
        chunk_index = 0

        while start < len(tokens):
            end = min(start + settings.chunk_size, len(tokens))
            chunk_text = tokenizer.decode(tokens[start:end])
            chunks.append({
                "text": chunk_text,
                "source": page["source"],
                "page": page["page"],
                "chunk_index": chunk_index,
            })
            chunk_index += 1
            if end == len(tokens):
                break
            start += settings.chunk_size - settings.chunk_overlap

    logger.info("Created %d chunks", len(chunks))
    return chunks


def _embed_chunks(chunks: list[dict]) -> np.ndarray:
    """Embed all chunk texts via OpenAI. Returns float32 numpy array."""
    texts = [c["text"] for c in chunks]
    all_embeddings: list[list[float]] = []
    batch_size = 100

    for i in range(0, len(texts), batch_size):
        batch = texts[i: i + batch_size]
        response = client.embeddings.create(
            model=settings.openai_embedding_model,
            input=batch,
        )
        all_embeddings.extend(item.embedding for item in response.data)
        logger.info(
            "Embedded %d / %d chunks",
            min(i + batch_size, len(texts)),
            len(texts),
        )

    return np.array(all_embeddings, dtype=np.float32)


def _load_index() -> None:
    """Load persisted FAISS index and chunks from disk."""
    global _index, _chunks
    _index = faiss.read_index(str(INDEX_FILE))
    with open(CHUNKS_FILE, "rb") as f:
        _chunks = pickle.load(f)
    logger.info("Vector store loaded from disk: %d vectors", _index.ntotal)


def build_index(force: bool = False) -> None:
    """
    Build and persist the FAISS index.
    Skips re-indexing if source PDFs haven't changed (unless force=True).
    """
    global _index, _chunks
    VECTOR_STORE_PATH.mkdir(exist_ok=True)
    current_hash = _compute_source_hash()

    if (
        not force
        and INDEX_FILE.exists()
        and CHUNKS_FILE.exists()
        and HASH_FILE.exists()
        and HASH_FILE.read_text().strip() == current_hash
    ):
        logger.info("Vector store is up to date — skipping re-index")
        _load_index()
        return

    logger.info("Building vector store...")
    pages = _extract_text_from_sources()

    if not pages:
        logger.warning("No PDF content found in '%s' — skipping index build", settings.knowledge_resources_dir)
        return

    chunks = _chunk_text(pages)
    embeddings = _embed_chunks(chunks)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    faiss.write_index(index, str(INDEX_FILE))
    with open(CHUNKS_FILE, "wb") as f:
        pickle.dump(chunks, f)
    HASH_FILE.write_text(current_hash)

    _index = index
    _chunks = chunks
    logger.info(
        "Vector store built — %d vectors, dim=%d, saved to '%s'",
        index.ntotal,
        dimension,
        VECTOR_STORE_PATH,
    )


def query(question: str, top_n: int | None = None) -> list[dict]:
    """
    Return the top-N most relevant chunks for the given question.
    Auto-loads index from disk if not already in memory.
    """
    global _index, _chunks

    if _index is None:
        if INDEX_FILE.exists():
            _load_index()
        else:
            logger.warning("Vector store not built yet — returning empty results")
            return []

    n = top_n or settings.rag_top_n

    response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=[question],
    )
    question_vec = np.array([response.data[0].embedding], dtype=np.float32)

    distances, indices = _index.search(question_vec, n)

    results: list[dict] = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        chunk: dict = dict(_chunks[int(idx)])
        chunk["score"] = float(dist)
        results.append(chunk)

    return results


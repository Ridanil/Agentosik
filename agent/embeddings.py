"""
Локальные эмбеддинги для семантического (векторного) поиска — RAG-компонент
(п.6, п.22 ТЗ: "упрощает будущий переход на embeddings/vector search").

Работает полностью локально, без сторонних API — эмбеддинги не покидают машину
пользователя, в духе п.11 ТЗ (экономия ресурсов / локальность). Используется
multilingual-модель, чтобы корректно работать с русскоязычными каналами.
"""
import asyncio

import numpy as np
from sentence_transformers import SentenceTransformer

from utils.logger import get_logger

logger = get_logger(__name__)

# Лёгкая multilingual-модель — хороший баланс качества/скорости для CPU.
# При необходимости можно заменить на paraphrase-multilingual-mpnet-base-v2 (точнее, но тяжелее).
EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Загружаю модель эмбеддингов: %s (первый запуск скачает ~470MB)", EMBEDDING_MODEL_NAME)
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def _encode_sync(texts: list[str]) -> np.ndarray:
    model = _get_model()
    vectors = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,  # нормализация -> скалярное произведение = косинусная близость
        convert_to_numpy=True,
    )
    return vectors.astype(np.float32)


async def embed_texts(texts: list[str]) -> np.ndarray:
    """Считает эмбеддинги пачкой. encode() — блокирующая CPU-операция, поэтому
    уводим её в отдельный поток, чтобы не блокировать event loop (сборщик и бот
    работают асинхронно и не должны друг друга подвешивать)."""
    if not texts:
        return np.zeros((0, EMBEDDING_DIM), dtype=np.float32)
    return await asyncio.to_thread(_encode_sync, texts)


async def embed_text(text: str) -> np.ndarray:
    vectors = await embed_texts([text])
    return vectors[0]


def vector_to_blob(vector: np.ndarray) -> bytes:
    return vector.astype(np.float32).tobytes()


def blob_to_vector(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)

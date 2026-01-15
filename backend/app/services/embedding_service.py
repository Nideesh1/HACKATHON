import json
import numpy as np
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer
from typing import Optional

from app.config import settings


class EmbeddingService:
    _instance: Optional["EmbeddingService"] = None
    _model: Optional[SentenceTransformer] = None
    _index: Optional[faiss.IndexFlatL2] = None
    _chunk_map: list[tuple[str, int]] = []  # (doc_id, chunk_index)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            print(f"Loading embedding model: {settings.embedding_model}")
            self._model = SentenceTransformer(settings.embedding_model)
            self._load_index()

    def _get_index_path(self) -> Path:
        return settings.embeddings_dir / "faiss.index"

    def _get_map_path(self) -> Path:
        return settings.embeddings_dir / "chunk_map.json"

    def _load_index(self) -> None:
        """Load existing index if available."""
        index_path = self._get_index_path()
        map_path = self._get_map_path()

        if index_path.exists() and map_path.exists():
            self._index = faiss.read_index(str(index_path))
            with open(map_path, "r") as f:
                self._chunk_map = [tuple(item) for item in json.load(f)]
            print(f"Loaded index with {self._index.ntotal} vectors")
        else:
            # Create empty index
            dim = self._model.get_sentence_embedding_dimension()
            self._index = faiss.IndexFlatL2(dim)
            self._chunk_map = []
            print("Created new empty index")

    def _save_index(self) -> None:
        """Save index to disk."""
        faiss.write_index(self._index, str(self._get_index_path()))
        with open(self._get_map_path(), "w") as f:
            json.dump(self._chunk_map, f)

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text."""
        return self._model.encode([text], convert_to_numpy=True)[0]

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed multiple texts."""
        return self._model.encode(texts, convert_to_numpy=True)

    def add_document_chunks(
        self, doc_id: str, chunks: list[str]
    ) -> None:
        """Add document chunks to the index."""
        if not chunks:
            return

        embeddings = self.embed_texts(chunks)

        # Add to index
        self._index.add(embeddings.astype(np.float32))

        # Update chunk map
        for i in range(len(chunks)):
            self._chunk_map.append((doc_id, i))

        self._save_index()
        print(f"Added {len(chunks)} chunks for document {doc_id}")

    def remove_document(self, doc_id: str) -> None:
        """Remove document from index (requires rebuild)."""
        # Find indices to keep
        indices_to_keep = [
            i for i, (did, _) in enumerate(self._chunk_map) if did != doc_id
        ]

        if len(indices_to_keep) == len(self._chunk_map):
            return  # Document not in index

        if not indices_to_keep:
            # Reset to empty index
            dim = self._model.get_sentence_embedding_dimension()
            self._index = faiss.IndexFlatL2(dim)
            self._chunk_map = []
        else:
            # Rebuild index with remaining vectors
            all_vectors = faiss.rev_swig_ptr(
                self._index.get_xb(), self._index.ntotal * self._index.d
            ).reshape(self._index.ntotal, self._index.d)

            kept_vectors = all_vectors[indices_to_keep]
            dim = self._model.get_sentence_embedding_dimension()
            new_index = faiss.IndexFlatL2(dim)
            new_index.add(kept_vectors.astype(np.float32))

            self._index = new_index
            self._chunk_map = [self._chunk_map[i] for i in indices_to_keep]

        self._save_index()
        print(f"Removed document {doc_id} from index")

    def search(self, query: str, top_k: int = None) -> list[tuple[str, int, float]]:
        """Search for similar chunks. Returns (doc_id, chunk_index, distance)."""
        top_k = top_k or settings.top_k

        if self._index.ntotal == 0:
            return []

        query_embedding = self.embed_text(query).reshape(1, -1).astype(np.float32)
        distances, indices = self._index.search(query_embedding, min(top_k, self._index.ntotal))

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self._chunk_map):
                doc_id, chunk_idx = self._chunk_map[idx]
                results.append((doc_id, chunk_idx, float(dist)))

        return results

    def get_index_size(self) -> int:
        """Get number of vectors in index."""
        return self._index.ntotal if self._index else 0


# Singleton instance - lazy loaded
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

#from sentence_transformers import SentenceTransformer
from .embedder import Embedder

class HuggingFaceEmbedder(Embedder):
    def __init__(self, model_name: str = "sentence-transformers/intfloat/e5-base-v2"): # или all-MiniLM-L6-v2
       # self.model = SentenceTransformer(model_name)
        pass

    def embed_text(self, text: str) -> list[float]:
        return self.model.encode(text, convert_to_numpy=True).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, convert_to_numpy=True).tolist()
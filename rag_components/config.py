from dataclasses import dataclass, field
from typing import List
from lightrag.utils import get_env_value



@dataclass
class RAGConfig:
    """Configuration class for RAG with environment variable support"""
    # Directory Configuration
    # ---
    working_dir: str = field(default=get_env_value("WORKING_DIR", "./rag_storage", str))
    """Directory where RAG storage and cache files are stored."""

    # Context Extraction Configuration
    # ---
    context_window: int = field(default=get_env_value("CONTEXT_WINDOW", 1, int))
    """Number of pages/chunks to include before and after current item for context."""

    context_mode: str = field(default=get_env_value("CONTEXT_MODE", "page", str))
    """Context extraction mode: 'page' for page-based, 'chunk' for chunk-based."""

    max_context_tokens: int = field(default=get_env_value("MAX_CONTEXT_TOKENS", 1500, int))

    chunk_overlap: int = field(default=get_env_value("CHUNK_OVERLAP",2, int))

    chunk_size: int = field(default=get_env_value("CHUNK_SIZE",2, int))

    top_k: int = field(default=get_env_value("TOP_K",3, int))



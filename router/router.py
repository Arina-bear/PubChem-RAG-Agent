from enum import Enum, auto
from abc import ABC, abstractmethod
from typing import List
import re
#from loguru import logger

class QueryType(Enum):
    """
    Enum for supported query types.
    """
    SIMPLE = auto()
    COMPLEX = auto()
    NONTYPE=auto()


class RoutingStrategy(ABC):
    """
    Abstract base class for query routing strategies.
    """

    @abstractmethod
    def route_query(self, query: str) -> QueryType:
        pass


class SimpleKeywordStrategy(RoutingStrategy):
    """
    Strategy to classify queries based on keywords and query length.
    """

    SIMPLE_KEYWORDS: List[str] = [
    "how much",
    "mass",
    "weight",
    "how many atoms",
    "molecular mass",
    "formula",
    "find the mass",
    "find the formula"
    ]

    COMPLEX_KEYWORDS: List[str] = [
        "how it works",
        "mechanism",
        "explain",
        "describe",
        "why",
        "compare",
        "how",
        "influence",
        "interaction"
    ]

    MAX_SIMPLE_LENGTH: int = 30

    def clear_question(self, query: str) -> str:
        """
        Normalize text before classification
        """
        query = query.lower()
        query = re.sub(r"\s+", " ", query)
        return query.strip()
    
    def _is_short_query(self, query: str) -> bool:
        """Check if query is short (≤ MAX_SIMPLE_LENGTH)"""
        return len(query) <= self.MAX_SIMPLE_LENGTH
   
    def route_query(self, query: str) -> QueryType:

        query_lower = self.clear_question(query)

        if self._is_short_query(query_lower):
            return QueryType.SIMPLE
         
        for keyword in sorted(self.SIMPLE_KEYWORDS, key=len, reverse=True):
            if keyword in query_lower:
                return QueryType.SIMPLE
            
        for keyword in sorted(self.COMPLEX_KEYWORDS, key=len, reverse=True):
            if keyword in query_lower:
                return QueryType.COMPLEX
    
        return QueryType.NONTYPE

class QueryRouter:
    """
    Main router class
    """

    def __init__(self, strategy: RoutingStrategy = None):
        self._strategy = strategy if strategy else SimpleKeywordStrategy()

    def route(self, query: str) -> QueryType:
        """
        Route query to type
        """
        return self._strategy.route_query(query)

    def set_strategy(self, strategy: RoutingStrategy):
        """
        Change routing strategy dynamically
        """
        self._strategy = strategy
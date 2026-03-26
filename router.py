from enum import Enum, auto
from abc import ABC, abstractmethod
from typing import List
import re


class QueryType(Enum):
    """
    Enum for supported query types.
    """
    SIMPLE = auto()
    COMPLEX = auto()


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
        "сколько",
        "масса",
        "вес",
        "сколько атомов",
        "молекулярная масса",
        "формула",
        "найди массу",
        "найди формулу"
    ]

    COMPLEX_KEYWORDS: List[str] = [
        "как работает",
        "механизм",
        "объясни",
        "опиши",
        "почему",
        "сравни",
        "каким образом",
        "влияние",
        "взаимодействие"
    ]

    MAX_SIMPLE_LENGTH: int = 60

    def normalize(self, query: str) -> str:
        """
        Normalize text before classification
        """
        query = query.lower()
        query = re.sub(r"\s+", " ", query)
        return query.strip()

    def route_query(self, query: str) -> QueryType:
        query = self.normalize(query)

        # Check complex keywords first
        for keyword in self.COMPLEX_KEYWORDS:
            if keyword in query:
                return QueryType.COMPLEX

        # Check simple keywords
        for keyword in self.SIMPLE_KEYWORDS:
            if keyword in query:
                return QueryType.SIMPLE

        # Fallback to length heuristic
        if len(query) > self.MAX_SIMPLE_LENGTH:
            return QueryType.COMPLEX

        return QueryType.SIMPLE


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
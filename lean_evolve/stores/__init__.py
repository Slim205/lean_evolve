from __future__ import annotations
from typing import Any

from abc import ABC, abstractmethod


class Solution(ABC):
    """
    Base class for a solution.
    """

    @abstractmethod
    def set_rating(self, rating: Any) -> None:
        """
        Persist the rating for this solution, if desired.
        """
        pass


class Store(ABC):
    """
    Base class for store of current solutions.
    """

    # TODO: Fill in
    @abstractmethod
    def sample(self) -> Solution:
        """
        Sample a solution from the store.
        """
        pass

    @abstractmethod
    def add(self, solution: Solution) -> None:
        """
        Add a solution to the store.
        """
        # Decides if the solution should be added to the store.
        # If needed, will remove a solution if the store is full.
        pass

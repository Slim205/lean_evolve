from abc import ABC, abstractmethod

from lean_evolve.stores import Solution


class Mutator(ABC):
    """
    Base class for a mutator.
    """

    @abstractmethod
    def mutate(self, solution: Solution) -> Solution:
        """
        Mutate a solution.
        """
        pass

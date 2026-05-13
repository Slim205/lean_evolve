from abc import ABC, abstractmethod

from lean_evolve.stores import Solution


class Rating(ABC):
    """
    Base class for a rating.
    """

    pass


class Rater(ABC):
    """
    Base class for a rater.
    """

    @abstractmethod
    def rate(self, solution: Solution) -> Rating:
        """
        Rate a solution.
        """
        pass

    @abstractmethod
    def is_correct(self, rating: Rating) -> bool:
        """
        Check if the rating is correct.
        """
        pass

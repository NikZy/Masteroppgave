from __future__ import annotations


class Model:
    """
    Interface for all models to implement in order to save and load
    """

    def save(self, path: str) -> None:
        """
        Save the model to the specified path.
        """
        pass

    def load(self, path: str) -> Model:
        """
        Load the model from the specified path.
        """
        pass

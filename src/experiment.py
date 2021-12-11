import logging
import os
from typing import Dict, List

from confuse.exceptions import NotFoundError
from genpipes.compose import Pipeline
from pandas import DataFrame

from src.data_types.model_type_enum import ModelTypeEnum
from src.model_strutures.local_univariate_arima import LocalUnivariateArima
from src.model_strutures.model_type import ModelType
from src.save_experiment_source.save_experiment_source import \
    SaveExperimentSource
from src.save_experiment_source.save_local_disk_source import \
    SaveLocalDiskSource


class Experiment:
    """
    The main class for running experiments.
    It contains logic for choosing model type, logging results, and saving results.
    """

    def __init__(
        self, title: str, description: str, save_sources_to_use: List[str] = [], save_source_options: Dict = {}
    ) -> None:
        self.title = title
        self.experiment_description = description
        self.save_sources = self._init_save_sources(save_sources_to_use, save_source_options)

    def _init_save_sources(self, save_sources: List[str], save_source_options: Dict) -> List[SaveExperimentSource]:
        sources = []
        for source in save_sources:
            if source == "disk":
                sources.append(SaveLocalDiskSource(options=save_source_options["disk"], title=self.title))
        return sources

    def choose_model_structure(self, model_options: Dict) -> ModelType:
        try:
            model_type = ModelTypeEnum[model_options["model_type"]]
            if model_type == ModelTypeEnum.local_univariate_arima:
                self.model = LocalUnivariateArima(model_options=model_options["arima"])
            return self.model

        except Exception as e:
            logging.error(
                f"Not a valid ModelType error: {e} \n \
                Valid ModelTypes are: {ModelTypeEnum.__members__}"
            )
            raise e

    def load_and_process_data(self, data_pipeline: Pipeline) -> DataFrame:
        logging.info("Loading data")
        logging.info(data_pipeline.__str__())
        return self.model.process_data(data_pipeline)

    def train_model(self) -> ModelType:
        logging.info("Training model")
        # TODO: Implement
        return self.model.train_model()

    def test_model(self) -> Dict:
        logging.info("Testing model")
        # TODO: Implement
        return self.model.test_model()

    def save_model(self, options: str) -> None:
        """
        Save the model and correspoding experiment to an already existing directory.
        """
        logging.info("Saving model")
        for save_source in self.save_sources:
            save_source.save_options(options)
            # Save options

            # TODO: Save models

            # Save metrics
            save_source.save_metrics([])

            # TODO: Save hyperparameters

            # TODO: Save figures

            # Save predictions
            # TODO: Implement

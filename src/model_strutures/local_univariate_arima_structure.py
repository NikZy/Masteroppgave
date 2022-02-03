import logging
import random
from typing import Dict, List, Optional, Tuple
import numpy as np
from genpipes.compose import Pipeline
from matplotlib.figure import Figure
from pandas.core.frame import DataFrame
from src.data_types.arima_model import ArimaModel
from src.data_types.i_model import IModel
from src.model_strutures.i_model_structure import IModelStructure
from src.pipelines import local_univariate_arima_pipeline as arima_pipeline
from src.save_experiment_source.i_log_training_source import ILogTrainingSource
from src.utils.error_calculations import calculate_error, calculate_mse
from src.utils.visuals import visualize_data_series
import warnings


class LocalUnivariateArimaStructure(IModelStructure):
    def __init__(
        self, log_sources: List[ILogTrainingSource], training_size: float, model_structure: List
    ) -> None:
        self.models = []
        self.log_sources = log_sources
        self.data_pipeline = None
        self.figures = []

        self.model_structures = model_structure
        self.training_size = training_size

        self.metrics: Dict = {}
        # Data
        self.training_set: DataFrame = None
        self.testing_set: DataFrame = None
        # Tuning
        self.tuning_parameter_error_sets = {}

    def init_models(self, load: bool = False):
        """
        Initialize models in the structure
        """
        self.models = list(
            map(
                lambda model_structure: ArimaModel(
                    log_sources=self.log_sources,
                    order=model_structure["order"],
                    name=model_structure["time_series_id"],
                    training_size=self.training_size,
                ),
                self.model_structures,
            )
        )

    def process_data(self, data_pipeline: Pipeline) -> Optional[DataFrame]:
        self.data_pipeline = arima_pipeline.local_univariate_arima_pipeline(
            data_pipeline, self.training_size
        )

        logging.info(f"data preprocessing steps: \n {self.data_pipeline}")
        self.training_set, self.testing_set = self.data_pipeline.run()
        return self.training_set

    def get_data_pipeline(self) -> Pipeline:
        return self.data_pipeline

    def train(self) -> IModelStructure:
        # TODO: Do something with the training metrics returned by 'train' method
        # TODO: Pass training data to the 'train' method
        for model in self.models:
            model.train(self.training_set)

    def test(self) -> Dict:
        # TODO: Do something with the test metrics data returned by the 'test' method
        # TODO: Pass test data to the 'test' method
        for model in self.models:
            # TODO: Make hardcoded value configurable
            model.test(self.testing_set, 10)

    # Exhaustive Grid Search of ARIMA model
    def auto_tuning(self, tuning_params: Dict = {}) -> None:
        # TODO: Compare using Cross-Validation
        # TODO: Add tuning parameters
        logging.info("Tuning model")
        forecasts = {}
        parameters = self._generate_parameter_grid()
        logging.info(f"Tuning parameter combinations to try are: {len(parameters)}#")

        for param in parameters:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                logging.info(f"Tuning ARIMA model. Parameters {param} used.")
                forecast = ArimaModel.method_evaluation(
                    param, self.training_set, self.testing_set, walk_forward=True
                )
                forecasts[f"{param}"] = forecast
        # Calculating Error
        error_parameter_sets = {}
        lowest_error, lowest_error_key = np.inf, list(forecasts.keys())[0]
        for key, forecast in forecasts.items():
            # Selection of error used for tuning
            if forecast is None:
                logging.info(f"Error with prediction key: {key}")
                continue
            err = calculate_mse(self.testing_set, forecast)
            error_parameter_sets[key] = err
            lowest_error_key = lowest_error_key if err > lowest_error else key
            lowest_error = lowest_error if err > lowest_error else err

        # Visualize prediction of best method
        self.figures = []
        self.figures.append(
            visualize_data_series(
                title=f"Value prediction ARIMA, {lowest_error_key}",
                data_series=[self.training_set, self.testing_set, forecasts[lowest_error_key]],
                data_labels=["Training_data", "Testing_data", "Forecast"],
                colors=["blue", "orange", "red"],
                x_label="date",
                y_label="hits",
            )
        )
        self.tuning_parameter_error_sets = error_parameter_sets
        self.tuning_parameter_error_sets["ARIMA"] = "MSE"
        return lowest_error_key

    def _generate_parameter_grid(
        self,
        p_range: Tuple[int, int] = (1, 7),
        d_range: Tuple[int, int] = (1, 7),
        q_range: Tuple[int, int] = (1, 14),
    ) -> List[Tuple[int, int, int]]:
        parameters = []
        for q in range(q_range[0], q_range[1] + 1):
            for d in range(d_range[0], d_range[1] + 1):
                for p in range(p_range[0], p_range[1] + 1):
                    parameters.append((p, d, q))
        return parameters

    def get_models(self) -> List[IModel]:
        return self.models

    def get_metrics(self) -> Dict:
        self.metrics = {}
        for model in self.models:
            self.metrics[model.get_name()] = model.get_metrics()
        return self.metrics

    def get_figures(self) -> List[Figure]:
        figures = []
        figures.extend(self.figures)
        for model in self.models:
            figures.extend(model.get_figures())
        return figures

    def get_tuning_parameters(self) -> Dict:
        return self.tuning_parameter_error_sets

    def __repr__(self):
        return f"<Local_univariate_arima> models: {self.models}"

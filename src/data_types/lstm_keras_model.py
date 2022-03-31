import logging
from abc import ABC
from typing import Any, Dict, List, Optional, Union

import keras
import numpy as np
import optuna
import tensorflow as tf
from numpy import ndarray
from src.data_types.modules.lstm_keras_module import LstmKerasModule
from src.data_types.neural_net_keras_model import NeuralNetKerasModel
from src.data_types.neural_net_model import NeuralNetModel
from src.optuna_tuning.local_univariate_lstm_keras_objecktive import (
    local_univariate_lstm_keras_objective,
)
from src.pipelines import local_univariate_lstm_keras_pipeline as lstm_keras_pipeline
from src.pipelines import local_univariate_lstm_pipeline as lstm_pipeline
from src.save_experiment_source.i_log_training_source import ILogTrainingSource
from src.save_experiment_source.local_checkpoint_save_source import LocalCheckpointSaveSource
from src.utils.config_parser import config
from src.utils.keras_optimizer import KerasOptimizer
from src.utils.prettify_dict_string import prettify_dict_string


class LstmKerasModel(NeuralNetKerasModel, ABC):
    def __init__(
        self,
        log_sources: List[ILogTrainingSource],
        time_series_id: str,
        params: Dict,
        optuna_trial: Optional[optuna.trial.Trial] = None,
    ):
        super(LstmKerasModel, self).__init__(
            log_sources,
            time_series_id,
            params,
            optuna_trial,
        )
        self.should_shuffle_batches = params["should_shuffle_batches"]

    def init_neural_network(
        self, params: dict, logger=None, return_model: bool = False, **xargs
    ) -> Union[keras.Sequential, None]:
        # When tuning, update model parameters with the ones from the trial
        self.hyper_parameters = params

        model = LstmKerasModule(**params).model
        optim = KerasOptimizer.get(params["optimizer_name"], learning_rate=params["learning_rate"])

        model.compile(optimizer=optim, loss="mse")
        logging.info(
            f"Model compiled with optimizer {params['optimizer_name']}\n"
            f"{prettify_dict_string(params)} \
            \n{model.summary()}"
        )

        if return_model:
            return model
        else:
            self.model = model

    def train(self, epochs: int = None, **xargs) -> Dict:
        logging.info("Training")
        is_tuning = xargs.pop("is_tuning") if "is_tuning" in xargs else False
        examples_to_drop_to_make_all_batches_same_size = (
            self.training_data[0].shape[0] % self.batch_size
        )
        logging.info(
            f"Examples to drop to make all batches same size: {examples_to_drop_to_make_all_batches_same_size}"
        )
        x_train, y_train = (
            self.training_data[0][:-examples_to_drop_to_make_all_batches_same_size],
            self.training_data[1][:-examples_to_drop_to_make_all_batches_same_size],
        )
        # Make validation set equal to one batch size
        x_val, y_val = (
            x_train[-self.batch_size :],
            y_train[-self.batch_size :],
        )
        # Drop validation set from training set
        x_train, y_train = (
            self.training_data[0][: -self.batch_size],
            self.training_data[1][: -self.batch_size],
        )
        history = self.model.fit(
            x=x_train,
            y=y_train,
            epochs=self.hyper_parameters["number_of_epochs"],
            batch_size=self.batch_size,
            shuffle=self.should_shuffle_batches,
            validation_data=(x_val, y_val),
            **xargs,
        )
        history = history.history

        if not is_tuning:
            training_predictions = self.predict(self.x_train)
            validation_predictions = self.predict(self.x_val)
            # Visualize
            self._visualize_predictions(
                (self.y_train[:, 0].flatten()),
                (training_predictions[:, 0].flatten()),
                "Training predictions",
            )
            self._visualize_predictions(
                self.y_val[:, 0, 0],
                validation_predictions[:, 0],
                "Validation predictions",
            )
            self._visualize_errors(
                [history["loss"], history["val_loss"]], ["Training_errors", "Validation_errors"]
            )

        self.metrics["training_error"] = history["loss"][-1]
        self.metrics["validation_error"] = history["val_loss"][-1]
        return self.metrics

    def _copy_trained_weights_to_model_with_different_batch_size(self) -> None:
        trained_weights = self.model.get_weights()
        params = self.hyper_parameters
        params["batch_size"] = 1
        prediction_model = self.init_neural_network(params=params, return_model=True)
        prediction_model.set_weights(trained_weights)
        self.prediction_model = prediction_model

    def predict_and_rescale(self, input_data: ndarray, targets: ndarray) -> ndarray:
        logging.info("Predicting")
        predictions = self.prediction_model.predict(input_data, batch_size=1)
        predictions_rescaled = self._rescale_data(predictions)
        targets_rescaled = self._rescale_data(targets)

        return predictions_rescaled, targets_rescaled

    def _rescale_data(self, data: ndarray) -> ndarray:
        return self.min_max_scaler.inverse_transform(data)

    def test(self, predictive_period: int = 7, single_step: bool = False) -> Dict:
        logging.info("Testing")
        results = self.prediction_model.evaluate(self.x_test, self.y_test, batch_size=1)

        # Visualize
        test_predictions = self.prediction_model.predict(self.x_test, batch_size=1)
        self._visualize_predictions(
            tf.reshape(self.y_test, (-1,)),
            tf.reshape(test_predictions, (-1,)),
            "Test predictions",
        )
        self.metrics["test_error"] = results
        return self.metrics

    def method_evaluation(
        self,
        parameters: Any,
        metric: str,
        singe_step: bool = True,
    ) -> Dict[str, Dict[str, str]]:
        logging.info("Tuning model")
        title, _ = LocalCheckpointSaveSource.load_title_and_description()
        study_name = f"{title}_{self.get_name()}"

        study = optuna.create_study(
            study_name=study_name,
            direction="minimize",
            sampler=optuna.samplers.TPESampler(),
            pruner=optuna.pruners.MedianPruner(),
            # TODO: IModel should not rely on the config. Fix this
            storage=f"sqlite:///{config['experiment']['save_source']['disk']['model_save_location'].get()}/optuna-tuning.db"
            if len(self.log_sources) > 0
            else None,
            load_if_exists=True,
        )
        logging.info(
            f"Loading or creating optuna study with name: {study_name}\n"
            f"Number of previous Trials with this name are #{len(study.trials)}"
        )
        study.optimize(
            lambda trial: local_univariate_lstm_keras_objective(
                trial=trial,
                hyperparameter_tuning_range=parameters,
                model=self,
            ),
            timeout=parameters["time_to_tune_in_minutes"] * 60,
            # TODO: Fix pytorch network to handle concurrency
            # n_jobs=8,  # Use maximum number of cores
            # n_trials=parameters["number_of_trials"],
            # show_progress_bar=False,
            callbacks=[self.log_trial],
        )
        id = f"{self.get_name()},{study.best_trial.number}"
        best_params = study.best_trial.params
        logging.info("Best params!", best_params)
        test_params = self.hyper_parameters.copy()
        test_params.update(best_params)
        logging.info("Params updated with best params", test_params)
        self.init_neural_network(test_params)
        best_score = study.best_trial.value
        logging.info(
            f"Best trial: {id}\n" f"best_score: {best_score}\n" f"best_params: {best_params}"
        )
        self._generate_optuna_plots(study)

        return {id: {"best_score": best_score, "best_params": best_params}}

    def get_model(self):
        return self.model

    def save(self, path: str) -> str:
        save_path = f"{path}{self.get_name}.h5"
        self.model.save_weights(save_path)
        return save_path

    def load(self, path: str) -> None:
        load_path = f"{path}{self.get_name}.h5"
        self.model.load_weights(load_path)

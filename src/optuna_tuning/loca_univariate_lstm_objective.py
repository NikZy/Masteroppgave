import logging
import typing
from collections import OrderedDict
from typing import Tuple, Dict, List

import optuna
from optuna.integration import PyTorchLightningPruningCallback, pytorch_lightning
from torch.utils.data import DataLoader

from typing import OrderedDict

from src.data_types.i_model import IModel
from src.data_types.modules.lstm_module import LstmModule
from src.save_experiment_source.i_log_training_source import ILogTrainingSource


def local_univariate_lstm_objective(
    trial: optuna.Trial,
    hyperparameter_tuning_range: OrderedDict[str, Tuple[int, int]],
    metric_to_use_when_tuning: str,
    model: IModel,
) -> float:
    params = hyperparameter_range_to_optuna_range(trial, hyperparameter_tuning_range)

    # The default logger in PyTorch Lightning writes to event files to be consumed by
    # TensorBoard. We create a simple logger instead that holds the log in memory so that the
    # final accuracy can be obtained after optimization. When using the default logger, the
    # final accuracy could be stored in an attribute of the `Trainer` instead.

    logging.info(
        f"Starting tuning trial number #{trial.number} of total {hyperparameter_tuning_range['number_of_trials']}\n"
        f"with params: {params}"
    )

    model._convert_dataset_to_dataloader(
        model.training_dataset,
        model.validation_dataset,
        model.testing_dataset,
        batch_size=params["batch_size"],
    )

    model.init_neural_network(
        params,
        callbacks=[PyTorchLightningPruningCallback(trial, monitor="validation_loss")],
    )

    errors = model.train(
        epochs=params["number_of_epochs"],
    )
    # TODO: Use config parameter 'metric'to use when tuning
    # score = model.calculate_mean_score(errors[""])

    return errors["validation_error"]


def hyperparameter_range_to_optuna_range(
    trial: optuna.Trial, config_params: OrderedDict[str, Tuple[int, int]]
) -> Dict[str, Tuple[float, float]]:
    return {
        "number_of_features": config_params["number_of_features"],
        "hidden_layer_size": trial.suggest_int(
            "hidden_layer_size", config_params["hidden_size"][0], config_params["hidden_size"][1]
        ),
        "input_window_size": config_params["input_window_size"],
        "output_window_size": config_params["output_window_size"],
        "number_of_layers": trial.suggest_int(
            "number_of_layers",
            config_params["number_of_layers"][0],
            config_params["number_of_layers"][1],
        ),
        "learning_rate": trial.suggest_loguniform(
            "learning_rate",
            float(config_params["learning_rate"][0]),
            float(config_params["learning_rate"][1]),
        ),
        "batch_first": True,
        "batch_size": trial.suggest_int(
            "batch_size", config_params["batch_size"][0], config_params["batch_size"][1]
        ),
        "dropout": trial.suggest_float(
            "dropout", config_params["dropout"][0], config_params["dropout"][1]
        ),
        "bidirectional": False,
        # TODO: Find out how to change optimizer hyperparameters
        "optimizer_name": trial.suggest_categorical(
            "optimizer_name", config_params["optimizer_name"]
        ),
        "number_of_epochs": trial.suggest_int(
            "number_of_epochs",
            config_params["number_of_epochs"][0],
            config_params["number_of_epochs"][1],
        ),
    }

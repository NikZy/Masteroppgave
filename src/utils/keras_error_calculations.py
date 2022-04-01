import logging
from collections import OrderedDict
from typing import Dict, List

import numpy as np
import pipe
import torch
from numpy import ndarray
from src.data_types.error_metrics_enum import ErrorMetricEnum
from src.utils.config_parser import config
from tensorflow import keras

pipe_enumurate = pipe.Pipe(lambda list: enumerate(list))


def generate_error_metrics_dict(errors: ndarray) -> Dict[str, float]:
    """
    Takes in a list of errors and returns a dictionary of error metrics names.
    Generate a dictionary of error metrics names and values.
    Example input: errors=[0.1, 0.2, 0.3]
    Example output: {"test_error_mse": 0.1, "test_error_mae": 0.2}
    """
    list_of_metrics = config["experiment"]["error_metrics"].get()
    assert len(list_of_metrics) == len(
        errors
    ), "Metrics defined in config is not the same length as the errors reported by Keras"
    metrics = dict(
        list(enumerate(list_of_metrics))  # enumerate returns a list of tuples (index, value)
        | pipe.map(
            lambda metric_id: (
                "test_" + metric_id[1],
                errors[metric_id[0]],
            )  # map the tuples to a dictionary
        )
    )

    return metrics


def config_metrics_to_keras_metrics() -> List:
    list_of_metrics = config["experiment"]["error_metrics"].get()
    keras_metrics = list(
        list_of_metrics
        | pipe.map(lambda metric_name: choose_metric(try_convert_to_enum(metric_name)))
    )
    return keras_metrics


def choose_metric(metric: ErrorMetricEnum):
    if metric == ErrorMetricEnum.MSE:
        return "mean_squared_error"
    elif metric == ErrorMetricEnum.MAE:
        return "mean_absolute_error"
    elif metric == ErrorMetricEnum.MASE:
        return "mean_absolute_scaled_error"
    elif metric == ErrorMetricEnum.SMAPE:
        return "symetric_mean_absolute_percentage_error"
    elif metric == ErrorMetricEnum.MAPE:
        return "mean_absolute_percentage_error"
    else:
        raise KeyError("Metric not implemented")


def try_convert_to_enum(key: str) -> ErrorMetricEnum:
    try:
        return ErrorMetricEnum[key]
    except KeyError:
        raise KeyError(
            f" '{key}' is not an implemented error metric. Valid values are {ErrorMetricEnum.__members__}"
        )

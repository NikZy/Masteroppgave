import logging
from abc import ABC
from typing import Dict, List, Optional, Tuple

import numpy as np
import optuna
import torch
from fastprogress import progress_bar
from matplotlib.figure import Figure
from numpy import float64, ndarray
from pandas import DataFrame
from src.data_types.i_model import IModel
from src.data_types.modules.lstm_module import LstmModule
from src.pipelines import local_univariate_lstm_pipeline as lstm_pipeline
from src.save_experiment_source.i_log_training_source import ILogTrainingSource
from torch import nn
from torch.autograd import Variable

from src.utils.visuals import visualize_data_series


class LstmModel(IModel, ABC):
    def __init__(
        self,
        log_sources: List[ILogTrainingSource],
        time_series_id: str,
        input_window_size: int = 1,
        output_window_size: int = 1,
        number_of_features: int = 1,
        number_of_layers: int = 1,
        hidden_layer_size: int = 20,
        learning_rate: float = 0.001,
        batch_size: int = 64,
        batch_first: bool = True,
        training_size: float = 0.8,
        dropout: float = 0.2,
        bidirectional: bool = False,
        optimizer_name: str = "Adam",
    ):

        # Init global variables
        self.log_sources: List[ILogTrainingSource] = log_sources
        self.name = time_series_id
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.batch_size = batch_size
        self.training_size = training_size
        self.input_window_size = input_window_size
        self.output_window_size = output_window_size

        self.training_data_loader = None
        self.validation_data_loader = None
        self.testing_data_loader = None
        self.min_max_scaler = None

        # Creating LSTM module
        self.model = LstmModule(
            input_window_size=input_window_size,
            number_of_features=number_of_features,
            hidden_layer_size=hidden_layer_size,
            output_size=output_window_size,
            num_layers=number_of_layers,
            learning_rate=learning_rate,
            batch_first=batch_first,
            dropout=dropout,
            bidirectional=bidirectional,
            optimizer_name=optimizer_name,
            device=self.device,
        )

        self.criterion = nn.MSELoss()
        self.optimizer = getattr(torch.optim, optimizer_name)(
            self.model.parameters(), lr=learning_rate
        )
        # TODO: Make using scheduler vs learning rate an option
        # self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        # self.optimizer, patience=500, factor=0.5, min_lr=1e-7, eps=1e-08
        # )
        if self.device == "cuda":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.criterion.cuda()

    def calculate_mean_score(self, losses: ndarray) -> float64:
        return np.mean(losses)

    def get_name(self) -> str:
        return self.name

    def train(self, epochs: int = 100) -> Dict:
        train_error = []
        val_error = []
        for epoch in progress_bar(range(epochs)):
            batch_train_error = []
            batch_val_error = []
            for x_batch, y_batch in self.training_data_loader:
                # the dataset "lives" in the CPU, so do our mini-batches
                # therefore, we need to send those mini-batches to the
                # device where the model "lives"
                x_batch = x_batch.to(self.device)
                y_batch = y_batch.to(self.device)
                loss = self._train_step(x_batch, y_batch)
                batch_train_error.append(loss)
            train_error.append(sum(batch_train_error) / len(batch_train_error))

            for x_val, y_val in self.validation_data_loader:
                x_val = x_val.to(self.device)
                y_val = y_val.to(self.device)
                val_loss = self._test_step(x_val, y_val)
                batch_val_error.append(val_loss)
            val_error.append(sum(batch_val_error) / len(batch_val_error))

            # TODO: Optuna!
            """
            if optuna_trial:
                accuracy = self.calculate_mean_score(val_losses)
                optuna_trial.report(accuracy, epoch)

                if optuna_trial.should_prune():
                    print("Pruning trial!")
                    raise optuna.exceptions.TrialPruned()
            """
            if epoch % 50 == 0:
                logging.info(f"Epoch: {epoch}, loss: {loss}. Validation losses: {val_loss}")
        # return losses, val_losses
        self._visualize_training_errors(training_error=train_error, validation_error=val_error)
        return {}  # TODO: Return dict with error metrics / loss

    # Builds function that performs a step in the train loop
    def _train_step(self, x, y) -> float:
        # Make prediction, and compute loss, and gradients
        self.model.train()
        yhat = self.model(x)
        loss = self.criterion(y, yhat)
        loss.backward()
        # Updates parameters and zeroes gradients
        self.optimizer.step()
        self.optimizer.zero_grad()
        # Returns the loss
        return loss.item()

    def _test_step(self, x, y) -> float:
        error = None
        with torch.no_grad():
            self.model.eval()
            yhat = self.model(x)
            loss = self.criterion(y, yhat)
            error = loss.item()
        return error

    def test(self, predictive_period: int = 6, single_step: bool = False) -> Dict:
        batch_test_error = []
        for x_test, y_test in self.test_loader:
            x_test = x_test.to(self.device)
            y_test = y_test.to(self.device)
            test_loss = self._test_step(x_test, y_test)
            batch_test_error.append(test_loss)
        error = sum(batch_test_error) / len(batch_test_error)
        return {"Error", error}

    def get_name(self) -> str:
        return self.name

    def process_data(self, data_set: DataFrame, training_size: float) -> None:
        data_pipeline = lstm_pipeline.local_univariate_lstm_pipeline(
            data_set=data_set,
            cat_id=self.get_name(),
            training_size=self.training_size,
            batch_size=self.batch_size,
            input_window_size=self.input_window_size,
            output_window_size=self.output_window_size,
        )

        for log_source in self.log_sources:
            log_source.log_pipeline_steps(data_pipeline.__repr__())

        (
            self.training_data_loader,
            self.validation_data_loader,
            self.testing_data_loader,
            self.min_max_scaler,
        ) = data_pipeline.run()

    def method_evaluation(
        self,
        parameters: List,
        metric: str,
        singe_step: bool = True,
    ) -> Dict[str, float]:
        """
        Evaluate model and calculate error of predictions for used for tuning evaluation
        """
        raise NotImplementedError()

    def get_figures(self) -> List[Figure]:
        """
        Return a list of figures created by the model for visualization
        """
        return self.figures

    def get_metrics(self) -> Dict:
        """
        Fetch metrics from model training or testing
        """
        raise NotImplementedError()

    def save(self, path: str) -> str:
        """
        Save the model to the specified path.
        :returns: Path to saved model file
        """
        raise NotImplementedError()

    def load(self, path: str) -> IModel:
        """
        Load the model from the specified path.
        """
        raise NotImplementedError()

    def get_predictions(self) -> Optional[Dict]:
        """
        Returns the predicted values if test() has been called.
        """
        raise NotImplementedError()

    def _visualize_training_errors(
        self, training_error: List[float], validation_error: List[float]
    ) -> None:
        # Visualize training and validation loss
        self.figures.append(
            visualize_data_series(
                title=f"{self.get_name()}# Training and Validation error",
                data_series=[training_error, validation_error],
                data_labels=["Training error", "Validation error"],
                colors=["blue", "orange"],
                x_label="Epoch",
                y_label="Error",
            )
        )

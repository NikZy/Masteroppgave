import logging
from ast import Tuple

import pytorch_lightning as pl
import torch
from src.utils.pytorch_error_calculations import calculate_errors
from torch import nn
from torch import Tensor
from torch.utils.data import DataLoader
from torch.autograd import Variable
from torch.nn import functional as F


class CNN_AE(pl.LightningModule):
    def __init__(self, **kwargs):
        super(CNN_AE, self).__init__()
        # TODO: Initial implementation is a simple Linear AE
        # self.encoder = nn.Sequential(nn.Linear(input_size, 64), nn.ReLU(), nn.Linear(64, 32))
        # self.decoder = nn.Sequential(nn.Linear(32, 64), nn.ReLU(), nn.Linear(64, input_size))

        self.encoder = nn.Sequential(nn.Conv1d(1, 8, 3), nn.ReLU(True), nn.Conv1d(8, 16, 5))
        # Decoder
        self.decoder = nn.Sequential(
            nn.ConvTranspose1d(16, 8, 5), nn.ReLU(True), nn.ConvTranspose1d(8, 1, 3)
        )
        self.criterion = nn.MSELoss()

    def configure_optimizers(self):
        # TODO: Config selection of optimizer
        optim = torch.optim.Adam(self.parameters(), lr=0.001)
        return optim

    def forward(self, x):
        x = x.view(x.shape[0], x.shape[2], x.shape[1])
        embeding = self.encoder(x)
        x_hat = self.decoder(embeding)
        x_hat = x_hat.view(x_hat.shape[0], x_hat.shape[2], x_hat.shape[1])
        return x_hat

    def training_step(self, batch: Tuple(Tensor), batch_idx: int):
        x, y = batch
        x_hat = self.forward(x)
        loss = self.criterion(x_hat, x)
        return loss

    def validation_step(self, batch: Tuple(Tensor), batch_idx: int):
        x, y = batch
        x_hat = self.predict_step(x, batch_idx)
        loss = self.criterion(x_hat, x)
        return loss

    def test_step(self, batch: Tuple(Tensor), batch_idx: int):
        x, y = batch
        x_hat = self.predict_step(x, batch_idx)
        loss = self.criterion(x_hat, x)
        return loss

    def visualize_predictions(self, dataset: DataLoader, first: bool = True):
        """
        Return selected targets and predictions for visualization of current predictive ability
        """
        # Visualize autoencoder (Only first value)
        targets = []
        predictions = []
        for batch_idx, batch in enumerate(dataset):
            x, y = batch
            x_hat = self.predict_step(x, batch_idx)
            if first:
                x = x[:, 0]
                x_hat = x_hat[:, 0]
            targets.extend(x.detach().numpy().flatten())
            predictions.extend(x_hat.detach().numpy().flatten())
        return targets, predictions

from typing import Dict

import pandas as pd
from genpipes.compose import Pipeline
from pandas.core.frame import DataFrame
from src.model_strutures.model_type import ModelType


class LocalUnivariateArima(ModelType):
    def __init__(self, model_options: Dict) -> None:
        # TODO: Implement
        pass

    def process_data(self, data_pipeline: Pipeline) -> DataFrame:
        # TODO: Implement
        pass

    def train(self) -> ModelType:
        # TODO: Implement
        pass

    def test(self) -> Dict:
        # TODO: Implement
        pass

# fmt: off
from genpipes.compose import Pipeline
from pandas import DataFrame

from src.pipelines.data_loader import dataframe_to_generator
import src.pipelines.market_insight_processing as market_processing


def local_univariate_lstm_pipeline(data_set: DataFrame, cat_id: str, training_size: float, batch_size: int) -> Pipeline:
    """
    Datapipeline which processes the data to be on the correct format
    before the local_univariate_lstm model can be applied.

    Args:
        :param cat_id:
        :param data_set:
        :param pipeline:
        :param training_size:
    Returns:
        Pipeline: The pipeline with the steps added.
    """
    return Pipeline(
        steps=[
            ("Convert input dataset to generator object", dataframe_to_generator, {"df": data_set}),
            (f"filter out category {cat_id})",
             market_processing.filter_by_cat_id,
             {"cat_id": cat_id},),
            ("choose columns 'interest' and 'date'", market_processing.choose_columns, {"columns": ["date", "interest"]}),
            ("fill in dates with zero values", market_processing.fill_in_dates, {}),
            (f"scale data between -1 and 1", market_processing.scale_data, {}),
            (f"split up into training set ({training_size}) and test set ({1 - training_size})",
             market_processing.split_into_training_and_test_set,
             {"training_size": training_size}),
            (f"TODO: convert to torch dataset with window size of ...", market_processing.print_info, {}),
            (f"TODO: convert to torch DataLoder with batch size of ...", market_processing.print_info, {}),
        ]
    )

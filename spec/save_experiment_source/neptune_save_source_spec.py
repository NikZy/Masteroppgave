from expects import be, be_false, be_true, expect
from expects.matchers.built_in import be_none
from mamba import after, before, description, it
from sklearn.linear_model import LogisticRegression
from src.data_types.sklearn_model import SklearnModel
from src.save_experiment_source.i_save_experiment_source import ISaveExperimentSource
from src.save_experiment_source.neptune_save_source import NeptuneSaveSource
from src.utils.config_parser import config

with description("NeptuneSaveSource", "api") as self:
    with before.all:
        options = {
            "project_id": "sjsivertandsanderkk/test-project",
        }
        self.save_source = NeptuneSaveSource(
            **options,
            title="test_experiment",
            description="Experiment for automated testing",
            tags=["test"],
        )

    with it("can upload options"):
        self.save_source.save_options("option1 option2")

    with it("can upload models"):
        models = [SklearnModel(LogisticRegression()), SklearnModel(LogisticRegression())]
        self.save_source.save_models(models)

    with it("can save metrics"):
        self.save_source.save_metrics(["mae: 0.1", "mse: 0.2"])

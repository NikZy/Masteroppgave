import os
import shutil
from pathlib import Path
from mockito import mock

import pytest
from expects import be_false, be_true, equal, expect, match
from expects.matchers.built_in import be_none
from genpipes.compose import Pipeline
from mamba import after, before, description, it
from matplotlib import pyplot as plt
from sklearn.linear_model import LogisticRegression
from spec.test_logger import init_test_logging
from spec.utils.test_data import test_data
from src.data_types.sklearn_model import SklearnModel
from src.save_experiment_source.i_log_training_source import ILogTrainingSource
from src.save_experiment_source.save_local_disk_source import SaveLocalDiskSource
from src.utils.combine_subfigure_titles import combine_subfigure_titles
from src.utils.temporary_files import temp_files

with description(SaveLocalDiskSource, "unit") as self:
    with before.all:
        init_test_logging()
        self.temp_location = "spec/temp/"
        try:
            os.mkdir(self.temp_location)
        except FileExistsError:
            pass

    with after.all:
        shutil.rmtree(self.temp_location)

    with before.each:
        self.options = {"model_save_location": self.temp_location}
        self.save_source = SaveLocalDiskSource(
            **self.options, title="test_experiment", tags=["test"]
        )

    with after.each:
        shutil.rmtree("spec/temp/test_experiment")

    with it("Throws exception when save location does already exist"):
        os.mkdir("spec/temp/this-folder-exists")
        with pytest.raises(FileExistsError):
            save_source = SaveLocalDiskSource(**self.options, title="this-folder-exists")

    with it("Initializes correctly when save location does not exist"):
        save_source = SaveLocalDiskSource(**self.options, title="this-folder-does-not-exist")

        expect(save_source.save_location.__str__()).to(
            match(Path("spec/temp/this-folder-does-not-exist").__str__())
        )

    with it("save options as options.yaml inside correct folder"):
        self.save_source._save_options("option 1\noption2")
        expect(os.path.isfile(f"{self.save_source.save_location}/options.yaml")).to(be_true)

    with it("saves metrix as metrics.txt inside correct folder"):
        self.save_source._save_metrics({"CPU": {"MAE": 5, "MSE": 6}, "GPU": {"MAE": 6, "MSE": 7}})
        expect(os.path.isfile("spec/temp/test_experiment/metrics.txt")).to(be_true)

    with it("Saves scikit-learn models correctly"):
        models = [
            SklearnModel(LogisticRegression(), mock(ILogTrainingSource)),
            SklearnModel(LogisticRegression(), mock(ILogTrainingSource)),
        ]
        self.save_source._save_models(models)
        expect(os.path.isfile("./spec/temp/test_experiment/model_0.pkl")).to(be_true)
        expect(os.path.isfile("./spec/temp/test_experiment/model_1.pkl")).to(be_true)
        expect(os.path.isfile("./spec/temp/test_experiment/model_3.pkl")).to(be_false)

    with it("Save raw data info correctly"):
        # Arrange
        file_config = {
            "raw_data": f"{self.save_source.save_location}/raw_data.csv",
            "category_data": f"{self.save_source.save_location}/category_data.csv",
        }
        for data_path_name, data_path in file_config.items():
            with open(data_path, "w") as f:
                f.write(f"Test data containing data from {data_path_name}")
        # Act
        self.save_source._save_dataset_version(file_config)
        # Assert
        expect(os.path.isfile(f"{self.temp_location}datasets.json"))

    with it("Loades scikit-learn models correctly"):
        # Arrange
        models = [SklearnModel(LogisticRegression(), mock(ILogTrainingSource))]
        self.save_source._save_models(models)
        # Act
        model = SklearnModel.load("spec/temp/test_experiment/model_0.pkl", [self.save_source])
        # Assert
        expect(model).to_not(be_none)

    with it("Saves figures as expected"):
        # Arrange
        fig, ax = plt.subplots()
        data = [1, 2, 3, 4, 5]
        ax.plot(data)
        ax.set_title("Test_title")

        self.save_source._save_figures([fig])
        expect(os.path.isfile("spec/temp/test_experiment/figures/Test_title.png")).to(be_true)

    with it("saves tags as expected"):
        expect(os.path.isfile("spec/temp/test_experiment/tags.txt")).to(be_true)

    with it("_combine_subfigure_titles combines multiple subfigures to a correct title"):
        # Create subplot
        fig, axs = plt.subplots(ncols=2, nrows=2, figsize=(5.5, 3.5), constrained_layout=True)
        for row in range(2):
            for col in range(2):
                axs[row, col].set_title(f"Subplot {row}-{col}")

        title = combine_subfigure_titles(fig)
        expect(title).to(match("Subplot 0-0, Subplot 0-1, Subplot 1-0, Subplot 1-1"))

    with it("Can call save figure twice without crashing"):
        fig, ax = plt.subplots()
        self.save_source._save_figures([fig])
        self.save_source._save_figures([fig])

    with it("creates a checkpoint save location when save epoch is above 0"):
        # Arrange
        temp = "temp/"
        with temp_files(temp):
            save_source = SaveLocalDiskSource(
                **self.options,
                title="test_checkpoints",
                description="test_checkpoints description",
                checkpoint_save_location=Path(temp + "/checkpoints"),
                log_model_every_n_epoch=1,
            )

            # Asses
            expect(save_source.checkpoint_save_location.__str__()).to(match("temp/checkpoints"))
            expect(save_source.checkpoint_save_location.is_dir()).to(be_true)
            expect(save_source.checkpoint_save_location.joinpath("options.yaml").is_file()).to(
                be_true
            )
            expect(
                save_source.checkpoint_save_location.joinpath("title-description.txt").is_file()
            ).to(be_true)

    with it("can run save_model_and_metadata() without crashing"):
        self.save_source.save_model_and_metadata(
            options="options",
            metrics={},
            datasets={},
            models=[],
            figures=[],
            data_pipeline_steps="steps",
        )

    with it("can save data_pipe_steps as expected"):
        """
        TODO til sindre i morgen: Need to create a dummy pipeline in order to test this!
        """
        pipeline = Pipeline(steps=[("load test data", test_data, {})])

        # noinspection PyTypeChecker
        self.save_source._save_data_pipeline_steps(data_pipeline_steps=pipeline.__str__())

        expect(
            os.path.isfile(self.save_source.save_location.joinpath("data_processing_steps.txt"))
        ).to(be_true)

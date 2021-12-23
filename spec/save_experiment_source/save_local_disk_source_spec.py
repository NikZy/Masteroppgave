import os
import shutil

import expects
import pytest
from expects import be_false, be_true, expect, be, match
from expects.matchers.built_in import be_none
from mamba import after, before, description, it
from matplotlib import pyplot as plt
from sklearn.linear_model import LogisticRegression

from spec.test_logger import init_test_logging
from src.data_types.sklearn_model import SklearnModel
from src.save_experiment_source.save_local_disk_source import (
    SaveLocalDiskSource,
    _combine_subfigure_titles,
)

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
        self.save_source = SaveLocalDiskSource(**self.options, title="test_experiment")

    with after.each:
        shutil.rmtree("spec/temp/test_experiment")

    with it("Throws exception when save location does already exist"):
        os.mkdir("spec/temp/this-folder-exists")
        with pytest.raises(FileExistsError):
            save_source = SaveLocalDiskSource(**self.options, title="this-folder-exists")

    with it("Initializes correctly when save location does not exist"):
        save_source = SaveLocalDiskSource(**self.options, title="this-folder-does-not-exist")
        assert save_source.save_location == "spec/temp/this-folder-does-not-exist"

    with it("save options as options.yaml inside correct folder"):
        self.save_source.save_options("option 1\noption2")
        expect(os.path.isfile("spec/temp/test_experiment/options.yaml")).to(be_true)

    with it("saves metrix as metrics.txt inside correct folder"):
        self.save_source.save_metrics(["mae: 0.1", "mse: 0.2"])
        expect(os.path.isfile("spec/temp/test_experiment/metrics.txt")).to(be_true)

    with it("Saves scikit-learn models correctly"):
        models = [SklearnModel(LogisticRegression()), SklearnModel(LogisticRegression())]
        self.save_source.save_models(models)
        expect(os.path.isfile("spec/temp/test_experiment/model_0.pkl")).to(be_true)
        expect(os.path.isfile("spec/temp/test_experiment/model_1.pkl")).to(be_true)
        expect(os.path.isfile("spec/temp/test_experiment/model_3.pkl")).to(be_false)

    with it("Loades scikit-learn models correctly"):
        # Arrange
        models = [SklearnModel(LogisticRegression())]
        self.save_source.save_models(models)
        # Act
        model = SklearnModel.load("spec/temp/test_experiment/model_0.pkl")
        # Assert
        expect(model).to_not(be_none)

    with it("Saved figures as expected"):
        # Arrange
        fig, ax = plt.subplots()
        data = [1, 2, 3, 4, 5]
        ax.plot(data)
        ax.set_title("Test_title")

        self.save_source.save_figures([fig])
        expect(os.path.isfile("spec/temp/test_experiment/figures/Test_title.png")).to(be_true)

    with it("_combine_subfigure_titles combines multiple subfigures to a correct title"):
        # Create subplot
        fig, axs = plt.subplots(ncols=2, nrows=2, figsize=(5.5, 3.5), constrained_layout=True)
        for row in range(2):
            for col in range(2):
                axs[row, col].set_title(f"Subplot {row}-{col}")

        title = _combine_subfigure_titles(fig)
        expect(title).to(match("Subplot 0-0, Subplot 0-1, Subplot 1-0, Subplot 1-1"))

    with it("Can call save figure twice without crashing"):
        fig, ax = plt.subplots()
        self.save_source.save_figures([fig])
        self.save_source.save_figures([fig])

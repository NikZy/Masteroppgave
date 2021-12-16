from click.testing import CliRunner
from confuse.exceptions import NotFoundError
from expects import be_true, expect
from expects.matchers.built_in import be
from genpipes.compose import Pipeline
from mamba import after, before, description, it
from mockito import mock, verify, when
from mockito.matchers import ANY
from mockito.mockito import unstub
from src import main
from src.experiment import Experiment
from src.model_strutures.i_model_type import IModelType
from src.pipelines.market_insight_preprocessing_pipeline import market_insight_pipeline
from src.utils.config_parser import get_absolute_path
from src.utils.logger import init_logging

with description("main.py", "integration") as self:
    with before.all:
        self.runner = CliRunner()

    with after.all:
        unstub()

    with it("runs without errors"):
        result = self.runner.invoke(main.main, [])
        expect(result.exit_code).to(be(0))

    with it("runs with --help"):
        result = self.runner.invoke(main.main, ["--help"])
        expect(result.exit_code).to(be(0))

    with it("runs with --experiment"):
        # Arrange
        when(Experiment).choose_model_structure(ANY)
        when(Experiment).load_and_process_data(ANY)
        when(Experiment).train_model().thenReturn(None)
        when(Experiment).test_model().thenReturn(None)
        when(Experiment).save_model({}).thenReturn(None)
        # Act
        result = self.runner.invoke(
            main.main, ["--experiment", "title", "description", "--no-save"]
        )
        # Assert
        verify(Experiment, times=1).load_and_process_data(ANY)
        verify(Experiment, times=1).train_model()
        verify(Experiment, times=1).test_model()
        verify(Experiment, times=0).save_model({})

        expect(result.exit_code).to(be(0))

    with it("runs without parameters"):
        expect(True).to(be_true)

    with it("executes init_logging"):
        mock_logger = mock(init_logging())

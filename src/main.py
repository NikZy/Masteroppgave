from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple

import click

from src.continue_experiment import ContinueExperiment
from src.experiment import Experiment
from src.pipelines import market_insight_preprocessing_pipeline as pipeline
from src.save_experiment_source.local_checkpoint_save_source import LocalCheckpointSaveSource
from src.utils import logger
from src.utils.config_parser import config
from src.utils.extract_tags_from_config import extract_tags_from_config


@click.command()
@click.option(
    "--experiment", "-e", nargs=2, help="Experiment title and description. Title must be unique."
)
@click.option(
    "--save/--no-save",
    default=True,
    help="Boolean flag for saving the results or not. Overrides config.yaml.",
)
@click.option("--tune/--no-tune", default=False, help="Boolean flag for tuning the models or not.")
@click.option(
    "--continue-experiment", "-c", is_flag=True, help="Continues the last experiment executed."
)
@click.option("--tags", "-t", multiple=True, help="Tags to be added to the experiment.")
@click.option("--load", "-l", help="Loads an experiment from a given path.")
@click.option("--neptune-id", "-n", help="Neptune experiment id to load")
def main(
    experiment: Tuple[str, str],
    save: bool,
    tune: bool,
    continue_experiment: bool,
    tags: Tuple[str],
    load: str,
    neptune_id: str,
) -> int:

    log_level = config["logger"]["log_level"].get()
    log_file = config["logger"]["log_file"].get()
    logger.init_logging(log_level, log_file)
    logging.info("Started")

    if experiment:
        logging.info(f'Starting experiment: "{experiment[0]}": "{experiment[1]}"')

        save_source_to_use = config["experiment"]["save_sources_to_use"].get()
        config_tags = extract_tags_from_config()
        experiment_tags = list(tags) + config_tags

        experiment = Experiment(
            title=experiment[0],
            description=experiment[1],
            save_sources_to_use=save_source_to_use
            if (save and (not type(save_source_to_use) is type(None)))
            else [],
            save_source_options=config["experiment"]["save_source"].get() if save else {},
            experiment_tags=experiment_tags,
        )

        # TODO: Should options to save always be sendt with, both with save and no save?
        if tune:
            experiment.run_tuning_experiment(
                model_options=config["model"].get(),
                data_pipeline=pipeline.market_insight_pipeline(),
                save=save,
                options_to_save=config.dump(),
            )
        else:
            experiment.run_complete_experiment(
                model_options=config["model"].get(),
                data_pipeline=pipeline.market_insight_pipeline(),
                save=save,
                options_to_save=config.dump(),
            )
    elif continue_experiment:
        logging.info(f"Continues previous experiment")

        experiment_checkpoints_location = LocalCheckpointSaveSource().get_checkpoint_save_location()

        experiment = ContinueExperiment(
            experiment_checkpoints_location=experiment_checkpoints_location,
        )
        if tune:
            experiment.continue_tuning(save=save, options_to_save=(config.dump() if save else None))
        else:
            experiment.continue_experiment()
    elif load:
        load_path = Path(load)
        logging.info(f"Loading experiment from {load_path}")
        experiment = ContinueExperiment(
            # TODO: Rename parameter name
            experiment_checkpoints_location=load_path,
        )
        experiment.continue_experiment()

    logging.info("Finished")
    return 0


if __name__ == "__main__":
    main()

import configparser
import json
from pathlib import Path

import rlbottraining.exercise_runner as er
from rlbot.matchconfig.conversions import read_match_config_from_file
from rlbot.matchconfig.match_config import Team, PlayerConfig
from rlbottraining.training_exercise import Playlist

from src.utils.scenario_test_object import JSONObject
from replay_training import ReplayExercise

import os


cleanup = []


def create_bot_config(car) -> PlayerConfig:
    team = Team.BLUE if car.team == "0" else Team.ORANGE
    cfg_file_name = './replay_bot_' + car.id + '.cfg'
    with open('./replay_bot.cfg') as bot_cfg_file:
        with open(cfg_file_name, 'w') as real_cfg_file:
            lines = bot_cfg_file.readlines()
            for line in lines:
                if line.find('name') > -1:
                    line = 'name = ReplayBot_' + car.id
                if line.find('lead') > -1 and not car.lead:
                    line = 'lead = False'
                real_cfg_file.write(line)
    cleanup.append(cfg_file_name)
    return PlayerConfig.bot_config(Path(__file__).absolute().parent / cfg_file_name, team)


def make_match_config(cars):
    """
    Creates a match config supplied with a player config that loads a bot that is configured by replay_bot.cfg
    """
    result_match_config = read_match_config_from_file(Path('replay_match.cfg'))
    player_configs = []
    for go in cars:
        player_configs.append(create_bot_config(go))
    result_match_config.player_configs = player_configs
    return result_match_config


def make_default_playlist() -> Playlist:
    # Load scenario file from settings to build the playlist
    with open('./settings.json') as settings_file:
        settings = json.load(settings_file, object_hook=JSONObject)
        with open(settings.path_to_settings) as scenario_settings_file:
            scenario_settings = json.load(scenario_settings_file, object_hook=JSONObject)
            with open(os.path.join(scenario_settings.szenario_path, scenario_settings.file_name)) as scenario_file:
                scenario = json.load(scenario_file, object_hook=JSONObject)

    # Build up the actual playlist with the previously created match config
    exercises = [
        ReplayExercise(name=scenario.name, scenario=scenario)
    ]

    match_config = make_match_config(filter(lambda go: go.gameObject == 'car', scenario.gameObjects))

    for e in exercises:
        e.match_config = match_config
    return exercises


if __name__ == "__main__":
    with er.setup_manager_context() as setup_manager:
        er.apply_render_policy(er.RenderPolicy.DEFAULT, setup_manager)
        seed = er.infinite_seed_generator()
        playlist = make_default_playlist()

        exercise = [er.TrainingExerciseAdapter(ex) for ex in playlist]
        result_iter = er.rlbot_run_exercises(setup_manager, exercise, seed)

        for _ in result_iter:
            pass
    print('cleaning up bot configs')
    for filename in cleanup:
        os.remove(filename)
    print('exercise finished')

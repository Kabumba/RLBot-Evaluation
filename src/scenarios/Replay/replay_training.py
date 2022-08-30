from dataclasses import dataclass, field

from rlbot.utils.game_state_util import GameState
from rlbottraining.common_graders.compound_grader import CompoundGrader
from rlbottraining.grading.grader import Grader
from rlbottraining.rng import SeededRandomNumberGenerator
from rlbottraining.training_exercise import Playlist
from rlbottraining.training_exercise import TrainingExercise

from src.graders.pass_graders import PassOnTimeout
from src.utils.scenario_test_object import JSONObject


class TestGrader(CompoundGrader):
    def __init__(self, timeout_seconds=100.0):
        super().__init__([
            PassOnTimeout(timeout_seconds),
        ])


@dataclass
class ReplayExercise(TrainingExercise):
    scenario: JSONObject = field(default_factory=JSONObject)
    grader: Grader = field(default_factory=TestGrader)

    def __post_init__(self):
        self.grader = TestGrader(self.scenario.time + 1)

    def make_game_state(self, rng: SeededRandomNumberGenerator) -> GameState:
        return GameState()


def make_default_playlist() -> Playlist:
    return [
        ReplayExercise('TestExercise'),
    ]

import bz2
import json
import pickle

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState, BOT_CONFIG_AGENT_HEADER, BOT_NAME_KEY
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.parsing.custom_config import ConfigObject
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics
from rlbot.utils.structures.game_data_struct import GameTickPacket

from src.utils.sequence import Sequence, ControlStep
from src.utils.scenario_test_object import JSONObject
from src.utils.game_tick_logger import GameTickLogger
from src.utils.vec import Location, Velocity, AngularVelocity, EulerAngles, UnitSystem
import os


class ReplayBot(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.replayData = None
        self.replayName = None
        self.active_sequence = None
        self.scenario = None
        self.logger = None
        self.log_path = None
        self.game_object = None
        self.lead = index == 0

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        """
        This function will be called by the framework many times per second. This is where you can
        see the motion of the ball, etc. and return controls to drive your car.
        """

        if self.active_sequence is None:
            self.setup()
            return SimpleControllerState()

        if self.active_sequence is not None and not self.active_sequence.done:
            if self.lead:
                self.logger.log(packet)
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls

        if self.lead and not self.logger.was_dumped:
            self.logger.dump()
        return SimpleControllerState()

    def setup(self):
        self.setup_game_state()
        self.setup_action_sequence()

    def setup_action_sequence(self):
        """
        Setup for the action sequence with given actions in the scenario file.
        If the actions don't fill the whole scenario time an idle action is appended so log more packets
        """
        self.send_quick_chat(team_only=False, quick_chat=QuickChatSelection.Information_IGotIt)
        if self.lead:
            self.logger = GameTickLogger(self.log_path)

        acc_durations = 0.0

        control_step_list = []
        for action in self.game_object.actions:
            control_step_list.append(
                ControlStep(duration=action.duration, controls=self.get_action_controls(action.inputs)))
            acc_durations += action.duration

        if self.scenario.time > acc_durations:
            control_step_list.append(ControlStep(duration=self.scenario.time - acc_durations,
                                                 controls=SimpleControllerState()))

        self.active_sequence = Sequence(control_step_list)

    @staticmethod
    def get_physics(values) -> 'Physics':
        """
        Returns a physics object with location, rotation, velocity and angular_velocity parses from a corresponding
        object that has all the needed attributes. (Supplied by the json config)
        """
        location = Location(values.location.x, values.location.y, values.location.z, UnitSystem.UNREAL)
        velocity = Velocity(values.velocity.x, values.velocity.y, values.velocity.z, UnitSystem.UNREAL)
        angular_velocity = AngularVelocity(values.angularVelocity.x, values.angularVelocity.y, values.angularVelocity.z,
                                           UnitSystem.UNREAL)
        rotation = EulerAngles(values.rotation.x, values.rotation.y, values.rotation.z, UnitSystem.UNREAL)
        return Physics(
            location=location.to_unreal_units().to_game_state_vector(),
            rotation=rotation.to_unreal_units().to_game_state_vector(),
            velocity=velocity.to_unreal_units().to_game_state_vector(),
            angular_velocity=angular_velocity.to_unreal_units().to_game_state_vector()
        )

    def setup_game_state(self):
        """
        Setup of the initial game state. This is made in the bot because setting the initial game state in the training
        exercise lead to certain time offsets in logging.
        """
        if not self.lead:
            return
        gs = GameState()
        gs.cars = dict()
        for go in self.scenario.gameObjects:
            if go.gameObject == 'car':
                gs.cars[len(gs.cars)] = CarState(physics=self.get_physics(go.startValues))
            elif go.gameObject == 'ball':
                gs.ball = BallState(physics=self.get_physics(go.startValues))

        self.set_game_state(gs)

    @staticmethod
    def get_action_controls(inputs):
        """
        Returns a SimpleControllerState with the given inputs set to given values of the inputs object.
        The object should have a name attribute corresponding to the input name in the ControllerState and a specified
        value.
        """
        control = SimpleControllerState()
        for i in inputs:
            setattr(control, i.name, i.value)

        return control

    def load_config(self, config_object_header):
        settings_path = config_object_header['settings'].value
        with open(settings_path) as settings_file:
            settings = json.load(settings_file, object_hook=JSONObject)
            self.replayName = os.listdir(settings.input_dir)[0].removesuffix(".pbz2")
            with bz2.BZ2File(settings.input_dir + "/" + self.replayName + ".pbz2", 'r') as logfile:
                pickle.dump(self.data, logfile)
            with open() as input_file:
                scenario_settings = json.load(input_file, object_hook=JSONObject)
                with open(os.path.join(scenario_settings.szenario_path, scenario_settings.file_name)) as scenario_file:
                    self.scenario = json.load(scenario_file, object_hook=JSONObject)
                    car_id = self.name.split('_')[1]
                    self.game_object = list(filter(lambda go: go.id == car_id, self.scenario.gameObjects))[0]
                    self.log_path = os.path.join(scenario_settings.results_path_rl_bot, self.scenario.name + '.json')
        self.lead = config_object_header['lead'].value

    @staticmethod
    def create_agent_configurations(config: ConfigObject):
        params = config.get_header(BOT_CONFIG_AGENT_HEADER)
        params.add_value('settings', str, default=None, description='Settings file that points to scenario settings')
        params.add_value('lead', bool, default=True, description='Determines if the bot is the leading bot in the '
                                                                 'test scenario responsible for logging')

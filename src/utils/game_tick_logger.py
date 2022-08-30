import bz2
import pickle

from rlbot.utils.structures.game_data_struct import GameTickPacket


class GameTickLogger:
    def __init__(self, log_path: str):
        self.log_path = log_path
        self.data = []
        self.was_dumped = False

    def dump(self):
        self.was_dumped = True
        with bz2.BZ2File(self.log_path, 'w') as logfile:
            pickle.dump(self.data, logfile)

    def log(self, packet: GameTickPacket):
        self.data.append(packet)

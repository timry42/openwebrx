from pycsdr.modules import ExecModule
from pycsdr.types import Format


class AcarsDecModule(ExecModule):
    def __init__(self):
        super().__init__(
            Format.FLOAT,
            Format.CHAR,
            ["acarsdec", "-s", "-o", "4"]
        )

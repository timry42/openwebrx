from pycsdr.modules import ExecModule
from pycsdr.types import Format
from owrx.aeronautical import AcarsProcessor


class AcarsDecModule(ExecModule):
    def __init__(self):
        super().__init__(
            Format.FLOAT,
            Format.CHAR,
            ["acarsdec", "-s", "-o", "4"]
        )


class AcarsParser(AcarsProcessor):
    def __init__(self):
        super().__init__("ACARS")

    def process(self, line):
        msg = super().process(line)
        if msg is not None:
            if "libacars" in msg:
                self.processAcars(msg)

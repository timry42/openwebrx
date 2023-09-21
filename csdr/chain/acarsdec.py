from pycsdr.modules import AmDemod
from owrx.acars.acarsdec import AcarsDecModule
from csdr.chain.demodulator import ServiceDemodulator
from csdr.module import JsonParser


class AcarsDec(ServiceDemodulator):
    def __init__(self):
        super().__init__([
            AmDemod(),
            AcarsDecModule(),
            JsonParser("ACARS"),
        ])

    def getFixedAudioRate(self) -> int:
        return 12500

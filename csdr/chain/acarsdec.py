from pycsdr.modules import AmDemod
from owrx.acars.acarsdec import AcarsDecModule, AcarsParser
from csdr.chain.demodulator import ServiceDemodulator
from csdr.module import JsonParser


class AcarsDec(ServiceDemodulator):
    def __init__(self):
        super().__init__([
            AmDemod(),
            AcarsDecModule(),
            AcarsParser(),
        ])

    def getFixedAudioRate(self) -> int:
        return 12500

    def supportsSquelch(self) -> bool:
        return False

from owrx.sstv import SstvParser
from csdr.chain.demodulator import SecondaryDemodulator, FixedAudioRateChain
from pycsdr.modules import FmDemod
from csdrsstv.modules import SstvDecoder


class Sstv(SecondaryDemodulator, FixedAudioRateChain):
    def __init__(self):
        super().__init__([
            FmDemod(),
            SstvDecoder(),
            SstvParser(),
        ])

    def getFixedAudioRate(self) -> int:
        return 12000

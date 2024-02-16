from owrx.sstv import SstvParser
from csdr.chain.demodulator import SecondaryDemodulator, FixedAudioRateChain
from pycsdr.modules import FmDemod, Buffer
from pycsdr.types import Format
from csdrsstv.modules import SstvDecoder
from owrx.feature import FeatureDetector
from typing import Optional


class Sstv(SecondaryDemodulator, FixedAudioRateChain):
    def __init__(self):
        self.imageBuffer = Buffer(Format.CHAR)
        super().__init__([
            FmDemod(),
            SstvDecoder(),
            SstvParser(),
        ])
        self.pngAdapter = None
        # tap into the pipeline to be able to send images off to MQTT
        if FeatureDetector().is_available("png"):
            # local import due to optional features
            from owrx.sstv.png import PngAdapter
            self.pngAdapter = PngAdapter()
            self.pngAdapter.setReader(self.imageBuffer.getReader())

    def _connect(self, w1, w2, buffer: Optional[Buffer] = None) -> None:
        if isinstance(w1, SstvDecoder):
            buffer = self.imageBuffer
        super()._connect(w1, w2, buffer)

    def stop(self):
        if self.pngAdapter is not None:
            self.pngAdapter.stop()
            self.pngAdapter = None
        super().stop()

    def getFixedAudioRate(self) -> int:
        return 12000

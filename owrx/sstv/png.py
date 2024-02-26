from pycsdr.types import Format
from owrx.sstv import ImageParser
from typing import List, Dict
from io import BytesIO
from owrx.reporting import ReportingEngine
import png
import base64


class PngAdapter(ImageParser):
    def __init__(self):
        self.vis = 0
        self.pixels = 0
        self.lines = 0
        self.meta = None
        self.image_data = []
        super().__init__()

    def getOutputFormat(self) -> Format:
        return Format.CHAR

    def startImage(self, vis: int, pixels: int, lines: int, meta: Dict) -> None:
        self.image_data = []
        self.vis = vis
        self.pixels = pixels
        self.lines = lines
        self.meta = meta

    def processLine(self, line: List[int]) -> None:
        self.image_data += [line]

    def finishImage(self):
        f = BytesIO()
        writer = png.Writer(self.pixels, self.lines, greyscale=False)
        writer.write(f, self.image_data)
        image_binary = bytes(f.getbuffer())
        if self.writer is not None:
            self.writer.write(image_binary)
        spot = {
            "mode": "SSTV",
            "vis": self.vis,
            "image": base64.b64encode(image_binary).decode('ascii'),
            "meta": self.meta,
        }
        ReportingEngine.getSharedInstance().spot(spot)
        f.close()

    def _checkStart(self) -> None:
        # we don't need a writer
        if self.reader is not None:
            self.start()

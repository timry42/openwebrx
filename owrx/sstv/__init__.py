from pycsdr.types import Format
from csdr.module import ThreadModule
import pickle
import struct
from abc import ABCMeta, abstractmethod
from typing import List, Dict

import logging

logger = logging.getLogger(__name__)


class ImageParser(ThreadModule, metaclass=ABCMeta):
    def run(self):
        stash = bytes()
        lines = 0
        pixels = 0
        synced = False
        headerFormat = "@hhhfff"
        headerSize = struct.calcsize(headerFormat)
        while self.doRun:
            data = self.reader.read()
            if data is None:
                self.doRun = False
            else:
                stash += data
                while not synced and len(stash) >= 4 + headerSize:
                    synced = stash[:4] == bytes(b"SYNC")
                    if synced:
                        (vis, pixels, lines, error, offset, visError) = struct.unpack(headerFormat, stash[4:4 + headerSize])
                        stash = stash[4 + headerSize:]
                        self.startImage(
                            vis,
                            pixels,
                            lines,
                            {
                                "error": error,
                                "offset": offset,
                                "visError": visError,
                            }
                        )
                    else:
                        # go search for sync... byte by byte.
                        stash = stash[1:]
                while synced and len(stash) >= pixels * 3:
                    line = [x for x in stash[:pixels * 3]]
                    stash = stash[pixels * 3:]
                    self.processLine(line)
                    lines -= 1
                    if lines == 0:
                        self.finishImage()
                        synced = False

    def getInputFormat(self) -> Format:
        return Format.CHAR

    @abstractmethod
    def startImage(self, vis: int, pixels: int, lines: int, meta: Dict) -> None:
        pass

    @abstractmethod
    def processLine(self, line: List[int]) -> None:
        pass

    @abstractmethod
    def finishImage(self):
        pass


class SstvParser(ImageParser):
    def getOutputFormat(self) -> Format:
        return Format.CHAR

    def startImage(self, vis: int, pixels: int, lines: int, meta: Dict) -> None:
        logger.debug("got image data: VIS = %i resolution: %i x %i", vis, pixels, lines)
        message = {
            "mode": "SSTV",
            "vis": vis,
            "resolution": {
                "width": pixels,
                "height": lines
            },
            "meta": meta,
        }
        self.writer.write(pickle.dumps(message))

    def processLine(self, line: List[int]) -> None:
        message = {
            "mode": "SSTV",
            "line": line,
        }
        self.writer.write(pickle.dumps(message))

    def finishImage(self):
        pass


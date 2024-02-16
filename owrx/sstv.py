from pycsdr.types import Format
from csdr.module import ThreadModule
import pickle
import struct

import logging

logger = logging.getLogger(__name__)


class SstvParser(ThreadModule):
    def __init__(self):
        super().__init__()

    def run(self):
        stash = bytes()
        lines = 0
        pixels = 0
        synced = False
        while self.doRun:
            data = self.reader.read()
            if data is None:
                self.doRun = False
            else:
                stash += data
                while not synced and len(stash) >= 10:
                    synced = stash[:4] == bytes(b"SYNC")
                    if synced:
                        (vis, pixels, lines) = struct.unpack("hhh", stash[4:10])
                        stash = stash[10:]
                        logger.debug("got image data: VIS = %i resolution: %i x %i", vis, pixels, lines)
                        message = {
                            "mode": "SSTV",
                            "vis": vis,
                            "resolution": {
                                "width": pixels,
                                "height": lines
                            }
                        }
                        self.writer.write(pickle.dumps(message))
                    else:
                        logger.debug("search for sync...")
                        # go search for sync... byte by byte.
                        stash = stash[1:]
                while synced and len(stash) >= pixels * 3:
                    line = [x for x in stash[:pixels * 3]]
                    stash = stash[pixels * 3:]
                    message = {
                        "mode": "SSTV",
                        "line": line,
                    }
                    self.writer.write(pickle.dumps(message))
                    lines -= 1
                    if lines == 0:
                        synced = False

    def getInputFormat(self) -> Format:
        return Format.CHAR

    def getOutputFormat(self) -> Format:
        return Format.CHAR

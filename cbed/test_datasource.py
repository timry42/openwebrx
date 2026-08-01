import struct
import unittest

from cbed.datasource import RandomWaterfallSource


class RandomWaterfallSourceTest(unittest.TestCase):
    def test_frame_uses_openwebrx_fft_wire_format(self):
        source = RandomWaterfallSource(fft_size=32)

        frame = source.make_frame()

        self.assertEqual(frame[0], 0x01)
        self.assertEqual(len(frame), 1 + 32 * 4)
        values = struct.unpack("<32f", frame[1:])
        self.assertTrue(all(-130 < value < -20 for value in values))


if __name__ == "__main__":
    unittest.main()
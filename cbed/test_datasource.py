import struct
import unittest

from cbed.datasource import RandomCompassSource, RandomWaterfallSource


class RandomWaterfallSourceTest(unittest.TestCase):
    def test_frame_uses_openwebrx_fft_wire_format(self):
        source = RandomWaterfallSource(fft_size=32)

        frame = source.make_frame()

        self.assertEqual(frame[0], 0x01)
        self.assertEqual(len(frame), 1 + 32 * 4)
        values = struct.unpack("<32f", frame[1:])
        self.assertTrue(all(-130 < value < -20 for value in values))


class RandomCompassSourceTest(unittest.TestCase):
    def test_message_contains_normalized_heading(self):
        source = RandomCompassSource()

        for _ in range(100):
            message = source.make_message()
            self.assertEqual(message["type"], "compass")
            self.assertGreaterEqual(message["value"]["heading"], 0)
            self.assertLess(message["value"]["heading"], 360)


if __name__ == "__main__":
    unittest.main()
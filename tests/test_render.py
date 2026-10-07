import math
import tempfile
import unittest
from pathlib import Path
import random
import struct
import zlib

import render


class RenderTests(unittest.TestCase):
    def test_quad_intersection(self):
        quad = render.Quad((0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 1))
        self.assertAlmostEqual(quad.intersect((.5, .5, -2), (0, 0, 1)), 2)
        self.assertIsNone(quad.intersect((2, .5, -2), (0, 0, 1)))
        self.assertIsNone(quad.intersect((.5, .5, 2), (0, 0, 1)))
        self.assertIsNone(quad.intersect((.5, .5, -2), (1, 0, 0)))

    def test_light_and_floor_receive_energy(self):
        surfaces, light = render.scene()
        camera = (0, 1, -3.2)
        target = render.add(light.corner, render.add(render.mul(light.u, .5), render.mul(light.v, .5)))
        self.assertEqual(render.trace(surfaces, light, camera, render.unit(render.sub(target, camera)), random.Random(1), 8), (14, 14, 14))
        color = render.trace(surfaces, light, (0, .2, .2), (0, -1, 0), random.Random(42), 8)
        self.assertTrue(all(math.isfinite(c) and c > 0 for c in color))

    def test_png_payload_and_checksums(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'image.png'
            render.write_png(path, 2, 1, bytes([255, 0, 0, 0, 255, 0]))
            data = path.read_bytes()
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            offset = 8
            payload = b''
            while offset < len(data):
                length = struct.unpack('!I', data[offset:offset+4])[0]
                kind = data[offset+4:offset+8]
                content = data[offset+8:offset+8+length]
                checksum = struct.unpack('!I', data[offset+8+length:offset+12+length])[0]
                self.assertEqual(checksum, zlib.crc32(kind+content) & 0xffffffff)
                if kind == b'IDAT': payload += content
                offset += length+12
            self.assertEqual(zlib.decompress(payload), bytes([0, 255, 0, 0, 0, 255, 0]))


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Dependency-free Cornell box path tracer. Coordinates: x right, y up, z into room."""
import argparse
import math
import random
import struct
import zlib
from pathlib import Path


def add(a, b): return tuple(x + y for x, y in zip(a, b))
def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def mul(a, s): return tuple(x * s for x in a)
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def unit(a): return mul(a, 1 / math.sqrt(dot(a, a)))


class Quad:
    def __init__(self, corner, u, v, color, emission=(0, 0, 0)):
        self.corner, self.u, self.v = corner, u, v
        self.color, self.emission = color, emission
        c = cross(u, v)
        self.area = math.sqrt(dot(c, c))
        self.normal = unit(c)
        self.uu, self.uv, self.vv = dot(u, u), dot(u, v), dot(v, v)
        self.det = self.uu * self.vv - self.uv ** 2

    def intersect(self, origin, direction):
        denominator = dot(self.normal, direction)
        if abs(denominator) < 1e-9:
            return None
        distance = dot(sub(self.corner, origin), self.normal) / denominator
        if distance <= 1e-5:
            return None
        relative = sub(add(origin, mul(direction, distance)), self.corner)
        du, dv = dot(relative, self.u), dot(relative, self.v)
        a = (du * self.vv - dv * self.uv) / self.det
        b = (dv * self.uu - du * self.uv) / self.det
        return distance if 0 <= a <= 1 and 0 <= b <= 1 else None


def scene():
    white, red, green = (.73, .73, .73), (.65, .05, .05), (.12, .45, .15)
    surfaces = [
        Quad((-1, 0, 0), (0, 0, 2), (2, 0, 0), white),
        Quad((-1, 2, 0), (2, 0, 0), (0, 0, 2), white),
        Quad((-1, 0, 2), (0, 2, 0), (2, 0, 0), white),
        Quad((-1, 0, 0), (0, 2, 0), (0, 0, 2), red),
        Quad((1, 0, 0), (0, 0, 2), (0, 2, 0), green),
    ]
    def box(cx, cz, sx, sz, height, angle):
        co, si = math.cos(angle), math.sin(angle)
        def point(x, y, z): return (cx + co*x + si*z, y, cz - si*x + co*z)
        corners = [point(-sx/2, 0, -sz/2), point(sx/2, 0, -sz/2),
                   point(sx/2, 0, sz/2), point(-sx/2, 0, sz/2)]
        for i in range(4):
            a, b = corners[i], corners[(i+1)%4]
            surfaces.append(Quad(a, (0, height, 0), sub(b, a), white))
        surfaces.append(Quad(add(corners[0], (0, height, 0)),
                             sub(corners[3], corners[0]), sub(corners[1], corners[0]), white))
    box(-.40, .70, .58, .58, .60, -.25)
    box(.38, 1.38, .60, .60, 1.18, .30)
    light = Quad((-.32, 1.99, .75), (.64, 0, 0), (0, 0, .50), (0, 0, 0), (14, 14, 14))
    surfaces.append(light)
    return surfaces, light


def closest(surfaces, origin, direction):
    best, distance = None, float('inf')
    for surface in surfaces:
        t = surface.intersect(origin, direction)
        if t is not None and t < distance:
            best, distance = surface, t
    return best, distance


def trace(surfaces, light, origin, direction, rng, max_depth):
    radiance, throughput = (0, 0, 0), (1, 1, 1)
    for depth in range(max_depth):
        surface, distance = closest(surfaces, origin, direction)
        if surface is None:
            break
        if surface is light:
            # Diffuse bounces use explicit light sampling, so count emission only for camera rays.
            if depth == 0 and dot(light.normal, direction) < 0:
                radiance = add(radiance, light.emission)
            break
        position = add(origin, mul(direction, distance))
        normal = surface.normal
        if dot(normal, direction) > 0:
            normal = mul(normal, -1)
        origin = add(position, mul(normal, 1e-4))
        target = add(light.corner, add(mul(light.u, rng.random()), mul(light.v, rng.random())))
        delta = sub(target, origin)
        squared_distance = dot(delta, delta)
        toward_light = unit(delta)
        cosine = max(0, dot(normal, toward_light))
        light_cosine = max(0, -dot(light.normal, toward_light))
        if cosine > 0 and light_cosine > 0:
            blocker, _ = closest(surfaces, origin, toward_light)
            if blocker is light:
                weight = cosine * light_cosine * light.area / (math.pi * squared_distance)
                radiance = add(radiance, tuple(throughput[i] * surface.color[i] * light.emission[i] * weight for i in range(3)))
        throughput = tuple(throughput[i] * surface.color[i] for i in range(3))
        if depth >= 3:
            survival = min(.95, max(throughput))
            if rng.random() >= survival:
                break
            throughput = mul(throughput, 1 / survival)
        angle, r2 = 2 * math.pi * rng.random(), rng.random()
        tangent = unit(cross((0, 1, 0) if abs(normal[1]) < .9 else (1, 0, 0), normal))
        bitangent = cross(normal, tangent)
        direction = add(mul(normal, math.sqrt(1-r2)),
                        add(mul(tangent, math.cos(angle)*math.sqrt(r2)), mul(bitangent, math.sin(angle)*math.sqrt(r2))))
    return radiance


def write_png(path, width, height, pixels):
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
    rows = b''.join(b'\0' + pixels[y*width*3:(y+1)*width*3] for y in range(height))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, 2, 0, 0, 0))
                     + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))


def positive(value):
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError('must be a positive integer')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--width', type=positive, default=256)
    parser.add_argument('--height', type=positive, default=256)
    parser.add_argument('--samples', type=positive, default=32, help='samples per pixel')
    parser.add_argument('--depth', type=positive, default=8, help='maximum ray bounces')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', type=Path, default=Path('output/cornell.png'))
    args = parser.parse_args()
    rng = random.Random(args.seed)
    surfaces, light = scene()
    pixels = bytearray()
    scale = math.tan(math.radians(39)/2)
    for y in range(args.height):
        for x in range(args.width):
            color = (0, 0, 0)
            for _ in range(args.samples):
                dx = (2*(x+rng.random())/args.width-1) * scale * args.width/args.height
                dy = (1-2*(y+rng.random())/args.height) * scale
                color = add(color, trace(surfaces, light, (0, 1, -3.2), unit((dx, dy, 1)), rng, args.depth))
            for c in color:
                # Reinhard tone mapping followed by the sRGB transfer function.
                linear = c / args.samples
                mapped = linear / (1 + linear)
                srgb = 12.92*mapped if mapped <= .0031308 else 1.055*mapped**(1/2.4)-.055
                pixels.append(round(255 * min(1, max(0, srgb))))
        if (y+1) % max(1, args.height//10) == 0 or y+1 == args.height:
            print(f'Rendering {y+1}/{args.height} rows', flush=True)
    write_png(args.output, args.width, args.height, bytes(pixels))
    print(f'Saved {args.output} ({args.width}x{args.height}, {args.samples} samples/pixel)')


if __name__ == '__main__':
    main()

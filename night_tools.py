from __future__ import division

from colour import Color
from math import log
from math import floor
import opc
import random
import time


STRAND_NUM_LEDS = 60
TOTAL_NUM_LEDS = STRAND_NUM_LEDS * 2


def put_encode(pixels):
    return [(c.red * 255, c.green * 255, c.blue * 255) for c in pixels]


def mux(bottom, top):
    return bottom + top


def fill(color, length=TOTAL_NUM_LEDS):
    return [color] * length


def add(p1, p2):
    return [Color(rgb=(c1.red + c2.red, c1.green + c2.green, c1.blue + c2.blue)) for c1, c2 in zip(p1, p2)]


def rotate(pixels, count):
    count = count % len(pixels)
    return pixels[-count:] + pixels[:-count]


def falloff(center_color, edge_color, center, length):
    length = max(1, length)
    if length > 1:
        gradient = list(center_color.range_to(edge_color, length))
    else:
        gradient = [center_color]
    if len(gradient) > int(NUM_LEDS / 2):
        gradient = gradient[:int(NUM_LEDS / 2)]
    full_gradient = list(reversed(gradient)) + gradient
    if len(full_gradient) < NUM_LEDS:
        full_gradient += fill(edge_color, NUM_LEDS - len(full_gradient))
    return rotate(full_gradient, center - length)


def background(f):
    core = Color("blue")
    core.luminance = min(f * 2, 1)
    pixels = falloff(core, BLACK, 30, int(NUM_LEDS * 2 * f))
    sun = Color("white")
    sun.luminance = min(f / 2, 0)
    pixels = add(pixels, falloff(sun, BLACK, 30, 5))
    return pixels


def bb(tK):
    """Start with a temperature, in Kelvin, somewhere between 1000 and 40000.  (Other values may work,
    but I can't make any promises about the quality of the algorithm's estimates above 40000 K.)
    Note also that the temperature and color variables need to be declared as floating-point.
    """
    tP = tK / 100.0

    if tP <= 66:
        r = 255
    else:
        r = 329.698727446 * ((tP - 60) ** -0.1332047592)

    if tP <= 66:
        g = 99.4708025861 * log(tP) - 161.1195681661
    else:
        g = 288.1221695283 * ((tP - 60) ** -0.0755148492)

    if tP >= 66:
        b = 255
    elif tP <= 19:
        b = 0
    else:
        b = 138.5177312231 * log(tP - 10) - 305.0447927307

    r = max(0, min(255, r))
    r = max(0, min(255, r))
    r = max(0, min(255, r))
    return Color(rgb=(r / 255.0, g / 255.0, b / 255.0))


def sprinkle(pixels, spark_color, density=0.1):
    out = list(pixels)
    pi = max(1, int(floor(density * len(pixels))))
    for i in random.sample(range(len(pixels)), pi):
        out[i] = spark_color
    return out


def linear_map(x, dl, du, rl, ru):
    pct = (x - dl) / (du - dl)
    return pct * (ru - rl) + rl

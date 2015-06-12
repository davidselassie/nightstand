from night_tools import linear_map
from night_tools import put_encode
from night_tools import fill
from night_tools import sprinkle
from night_tools import bb
from night_tools import rotate
from night_tools import STRAND_NUM_LEDS
from night_tools import mux
import opc
import time
import urllib.request
import json

from colour import Color

import json
from threading import Thread

from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler


c = opc.Client('localhost:7890')


class ColorThread(Thread):
    def run(self):
        p = fill(self.color)
        c.put_pixels(put_encode(p))
        # Put twice to "override" interpolation.
        c.put_pixels(put_encode(p))

    def kill(self):
        pass


class OffThread(ColorThread):
    name = 'Off'
    color = Color('black')


class OnThread(ColorThread):
    name = 'On'
    color = Color('white')


class LampThread(ColorThread):
    name = 'Lamp'
    color = bb(4000)


class HellThread(Thread):
    name = 'Hell'

    _alive = True

    def run(self):
        while self._alive:
            p = fill(Color('red'), STRAND_NUM_LEDS)
            p = sprinkle(p, Color('orange'), 0.1)
            p = mux(p, fill(Color('black'), STRAND_NUM_LEDS))
            c.put_pixels(put_encode(p))
            time.sleep(0.3)

    def kill(self):
        self._alive = False


def _make_pole(sections, num_leds):
    color_order = (
                Color('red'),
                Color('black'),
                Color('blue'),
                Color('black'),
                )
    pole = fill(Color('black'), num_leds)
    sect_len = int(num_leds / sections)
    for sect in range(sections):
        pole[sect * sect_len:(sect + 1) * sect_len] = (color_order[sect % len(color_order)], ) * sect_len
    return pole



class BarberThread(Thread):
    name = 'Barber'
    period_sec = 60

    _pole = _make_pole(8, STRAND_NUM_LEDS)
    _alive = True

    def run(self):
        while self._alive:
            theta = time.time() % self.period_sec / self.period_sec
            p = rotate(self._pole, int(theta * len(self._pole)))
            p = mux(p, p)
            c.put_pixels(put_encode(p))
            time.sleep(0.5)

    def kill(self):
        self._alive = False


class RainbowThread(Thread):
    name = 'Rainbow'
    period_sec = 120

    _alive = True

    def run(self):
        while self._alive:
            theta = time.time() % self.period_sec / self.period_sec
            p = fill(Color(hue=theta, saturation=1, luminance=0.5))
            c.put_pixels(put_encode(p))
            time.sleep(0.1)

    def kill(self):
        self._alive = False


def map_range(i, min_v, max_v, x):
    p = min(max(x - min_v, 0) / (max_v - min_v), 1.0)
    print('p = {0}'.format(p))
    return i[int(p * (len(i) - 1))]


class WeatherThread(Thread):
    name = 'Weather'

    _curl = 'https://api.forecast.io/forecast/89baad8cfc93b3899fb1fd580745b40c/37.812265,-122.280879'
    _alive = True

    _open_sky_color = Color('#18C0FF')
    _cloud_color = Color('#495167')

    def _get_temp_cc(self):
        resp_json = json.loads(urllib.request.urlopen(self._curl).read().decode('utf8'))
        temp = resp_json['currently']['temperature']
        cc = resp_json['currently']['cloudCover']
        print('temp = {0}, cc = {1}'.format(temp, cc))
        return temp, cc

    def _temp_to_color(self, temp):
        c = bb(linear_map(temp, 30, 100, 10000, 1000))
        return c

    def run(self):
        while self._alive:
            temp, cc = self._get_temp_cc()
            temp_color = self._temp_to_color(temp)
            ground_p = fill(temp_color, STRAND_NUM_LEDS)
            sky_p = fill(self._open_sky_color, STRAND_NUM_LEDS)
            sky_p = sprinkle(sky_p, self._cloud_color, cc)
            p = mux(ground_p, sky_p)
            c.put_pixels(put_encode(p))
            c.put_pixels(put_encode(p))
            time.sleep(15 * 60)

    def kill(self):
        self._alive = False


KNOWN_STATES = (OffThread, LampThread, OnThread, RainbowThread, HellThread, BarberThread, WeatherThread)
KNOWN_NAMES_TO_STATE = {
    state.name: state
    for state
    in KNOWN_STATES
}


daemon = OffThread()
daemon.start()


class NightstandHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global daemon
        if self.path == '/':
            self.send_response(200)
            self.end_headers()
            with open('index.html', 'br') as infile:
                self.wfile.write(infile.read())
        elif self.path == '/state':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({
                'states': [
                    {
                        'name': state.name,
                        'active': state.name == daemon.name,
                    }
                    for state
                    in KNOWN_STATES
                ],
            }, ensure_ascii=False).encode('utf-8'))
        elif self.path.startswith('/state/'):
            new_name = self.path.lstrip('/state/')
            daemon.kill()
            daemon.join(1)
            try:
                daemon = KNOWN_NAMES_TO_STATE[new_name]()
            except KeyError:
                self.send_error(400, 'Unknown state')
                return
            daemon.start()
            self.send_response(200)
        else:
            self.send_error(404)


if __name__ == '__main__':
    s = HTTPServer(('', 1987), NightstandHandler)
    s.serve_forever()

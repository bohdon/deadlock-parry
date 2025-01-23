from __future__ import annotations

import logging
import os.path
import random
import statistics
import time

import click
import pygame
import win32com.client
import win32con
import win32gui

__version__ = "1.0.3"

_file_dir = os.path.dirname(__file__)

LOG = logging.getLogger()
logging.basicConfig(format="%(asctime)s %(levelname)-8s %(message)s", level=logging.INFO)

DEFAULT_DELAY_MIN = 15
DEFAULT_DELAY_MAX = 240
DEFAULT_PARRY_WINDOW = 600


class ParryResult(object):
    def __init__(self, success: bool, response_time: float = 0):
        self.success = success
        self.response_time = response_time


class PunchGame(object):
    PUNCH_SOUND = "punch"
    PARRY_SOUND = "parry"
    HIT_SOUND = "hit"

    def __init__(self):
        # minimum delay between punches, in seconds
        self.delay_min = DEFAULT_DELAY_MIN
        # maximum delay between punches, in seconds
        self.delay_max = DEFAULT_DELAY_MAX
        # the maximum number of milliseconds allowed before the parry fails
        self.parry_window = DEFAULT_PARRY_WINDOW
        # the key binding for parry
        self.parry_key = pygame.K_f

        # the next time a punch should be triggered
        self._next_punch_time = -1
        # the actual time at which a punch started
        self._punch_start_time = -1
        self._is_punching = False

        self._window: pygame.Surface | None = None
        self._hwnd = None
        self._last_active_hwnd = None

        # a record of all results
        self.results: list[ParryResult] = []

        pygame.init()
        pygame.mixer.init()

    def set_parry_key(self, name: str):
        try:
            self.parry_key = pygame.key.key_code(name)
        except ValueError:
            LOG.warning(f"Unknown key name: {name}")
            pass

    def play_sound(self, name):
        path = os.path.join(_file_dir, "audio", f"{name}.wav")
        sound = pygame.mixer.Sound(path)
        sound.play()

    def start(self):
        LOG.info(f"Starting parry practice")
        LOG.info(f"Delay: {self.delay_min}..{self.delay_max}s")
        LOG.info(f"Parry Window: {self.parry_window}ms")
        LOG.info(f"Parry Key: {pygame.key.name(self.parry_key)}")
        LOG.info(f"Press Ctrl + C to quit.")

        # create a display to capture input
        self._window = pygame.display.set_mode()
        self._hwnd = pygame.display.get_wm_info()["window"]
        pygame.display.set_caption("Deadlock Parry Practice")

        # make window transparent
        win32gui.SetWindowLong(
            self._hwnd,
            win32con.GWL_EXSTYLE,
            win32gui.GetWindowLong(self._hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED,
        )
        # from 0..255
        transparency = 1
        win32gui.SetLayeredWindowAttributes(self._hwnd, 0, transparency, win32con.LWA_ALPHA)

        # start minimized
        self.deactivate_window()

        run = True
        while run:
            self._window.fill(0)

            # listen for parry input
            did_parry = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    run = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.deactivate_window()
                    elif event.key == pygame.K_c:
                        if event.mod & pygame.KMOD_CTRL:
                            LOG.info(f"Received Ctrl + C, exiting...")
                            run = False
                    elif event.key == self.parry_key:
                        did_parry = True
                    LOG.debug(f"KEYDOWN: {event.dict}")

            if not self._is_punching:
                if self._next_punch_time < 0:
                    self.schedule_punch()

                # wait for next punch
                if time.time() >= self._next_punch_time:
                    self.punch()

            if self._is_punching:
                elapsed_time_ms = (time.time() - self._punch_start_time) * 1000
                # check for key press
                if did_parry:
                    self.parry()
                elif elapsed_time_ms >= self.parry_window:
                    self.fail_parry()

            pygame.display.flip()

    def activate_window(self):
        if self._hwnd:
            # SetForegroundWindow won't work unless you send an alt key first
            shell = win32com.client.Dispatch("WScript.Shell")
            shell.SendKeys("%")
            win32gui.ShowWindow(self._hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self._hwnd)

    def deactivate_window(self):
        # restore focus to the previously focused window
        if self._hwnd:
            win32gui.ShowWindow(self._hwnd, win32con.SW_MINIMIZE)

    def schedule_punch(self):
        random_delay = random.uniform(self.delay_min, self.delay_max)
        self._next_punch_time = time.time() + random_delay
        LOG.debug(f"Next punch in {random_delay:.2f}s")

    def punch(self):
        # activate game window
        self.activate_window()

        self.play_sound(self.PUNCH_SOUND)
        self._is_punching = True
        self._punch_start_time = time.time()

        LOG.debug(f"Punch")

    def reset_punch(self):
        self._is_punching = False
        self._next_punch_time = -1
        # hide the game window
        self.deactivate_window()

    def parry(self):
        time_ms = round((time.time() - self._punch_start_time) * 1000)
        LOG.info(f"Parry success: {time_ms}ms")
        self.results.append(ParryResult(True, time_ms))

        self.play_sound(self.PARRY_SOUND)
        self.reset_punch()

        self.log_results_summary()

    def fail_parry(self):
        LOG.info("Parry failed, you died.")
        self.results.append(ParryResult(False))

        self.play_sound(self.HIT_SOUND)
        self.reset_punch()

        self.log_results_summary()

    def log_results_summary(self):
        successful_results = [r for r in self.results if r.success]
        num_total = len(self.results)
        num_success = len(successful_results)
        avg_response = 0
        if successful_results:
            avg_response = round(statistics.fmean([r.response_time for r in successful_results]))
        success_rate = num_success / float(num_total)
        LOG.info(f"{num_success} / {num_total} ({success_rate * 100:.2f}%), average response: {avg_response}ms")


@click.command()
@click.option(
    "-m",
    "--delay-min",
    type=int,
    default=DEFAULT_DELAY_MIN,
    help=f"The minimum delay before a random punch, in seconds (Default: {DEFAULT_DELAY_MIN})",
)
@click.option(
    "-x",
    "--delay-max",
    type=int,
    default=DEFAULT_DELAY_MAX,
    help=f"The max delay before a random punch, in seconds (Default: {DEFAULT_DELAY_MAX})",
)
@click.option(
    "-w",
    "--parry-window",
    type=int,
    default=DEFAULT_PARRY_WINDOW,
    help=f"The max duration for parrying before being hit, in milliseconds (Default: {DEFAULT_PARRY_WINDOW})",
)
@click.option(
    "-k",
    "--parry-key",
    default="f",
    help="The key binding for parry",
)
def main(delay_min, delay_max, parry_window, parry_key):
    timer = PunchGame()
    timer.delay_min = delay_min
    timer.delay_max = delay_max
    timer.parry_window = parry_window
    timer.set_parry_key(parry_key)
    timer.start()


if __name__ == "__main__":
    main()

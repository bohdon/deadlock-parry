from __future__ import annotations

import logging
import os.path
import random
import time

import click
import pygame
import win32com.client
import win32con
import win32gui

__version__ = "1.0.1"

_file_dir = os.path.dirname(__file__)

LOG = logging.getLogger()
logging.basicConfig(format="%(asctime)s %(levelname)-8s %(message)s", level=logging.INFO)


class PunchGame(object):
    PUNCH_SOUND = "punch"
    PARRY_SOUND = "parry"
    HIT_SOUND = "hit"

    def __init__(self):
        # minimum delay between punches, in seconds
        self.delay_min = 30
        # maximum delay between punches, in seconds
        self.delay_max = 300
        # the maximum number of milliseconds allowed before the parry fails
        self.parry_window = 750

        # the next time a punch should be triggered
        self._next_punch_time = -1
        # the actual time at which a punch started
        self._punch_start_time = -1
        self._is_punching = False

        self._window: pygame.Surface | None = None
        self._hwnd = None
        self._last_active_hwnd = None

    def play_sound(self, name):
        path = os.path.join(_file_dir, "audio", f"{name}.wav")
        sound = pygame.mixer.Sound(path)
        sound.play()

    def start(self):
        LOG.info(f"Starting parry practice")
        LOG.info(f"Delay: {self.delay_min}..{self.delay_max}s")
        LOG.info(f"Parry Window: {self.parry_window}ms")
        LOG.info(f"Press Ctrl + C to quit.")

        pygame.init()
        pygame.mixer.init()

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

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    run = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.deactivate_window()
                    if event.key == pygame.K_c:
                        if event.mod & pygame.KMOD_CTRL:
                            LOG.info(f"Received Ctrl + C, exiting...")
                            run = False
                    LOG.debug(f"KEYDOWN: {event.dict}")
                if event.type == pygame.MOUSEBUTTONDOWN:
                    LOG.debug(f"MOUSEBUTTONDOWN: {event.dict}")

            if not self._is_punching:
                if self._next_punch_time < 0:
                    self.schedule_punch()

                # wait for next punch
                if time.time() >= self._next_punch_time:
                    self.punch()

            if self._is_punching:
                elapsed_time_ms = (time.time() - self._punch_start_time) * 1000
                # check for key press
                if self.is_parry_key_pressed():
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
        LOG.info(f"Scheduled punch in {random_delay:.2f}s")

    def punch(self):
        # activate game window
        self.activate_window()

        self.play_sound(self.PUNCH_SOUND)
        self._is_punching = True
        self._punch_start_time = time.time()

        LOG.info(f"Punch started {self._punch_start_time}")

    def reset_punch(self):
        self._is_punching = False
        self._next_punch_time = -1
        # hide the game window
        self.deactivate_window()

    def is_parry_key_pressed(self):
        keys = pygame.key.get_pressed()
        return keys[pygame.K_f]

    def parry(self):
        time_ms = round((time.time() - self._punch_start_time) * 1000)
        LOG.info(f"Parry success: {time_ms}ms")
        self.play_sound(self.PARRY_SOUND)
        self.reset_punch()

    def fail_parry(self):
        LOG.info("Parry failed, you died.")
        self.play_sound(self.HIT_SOUND)
        self.reset_punch()


@click.command()
@click.option(
    "-m",
    "--delay-min",
    type=int,
    default=30,
    help="The minimum delay before a random punch, in seconds",
)
@click.option(
    "-x",
    "--delay-max",
    type=int,
    default=300,
    help="The maximum delay before a random punch, in seconds",
)
@click.option(
    "-w",
    "--parry-window",
    type=int,
    default=500,
    help="The maximum allowed duration for parrying before being hit, in milliseconds",
)
def main(delay_min, delay_max, parry_window):
    timer = PunchGame()
    timer.delay_min = delay_min
    timer.delay_max = delay_max
    timer.parry_window = parry_window
    timer.start()


if __name__ == "__main__":
    main()

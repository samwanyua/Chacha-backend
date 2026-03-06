"""
LED control service via GPIO for SpeechMaster.
Controls green, orange, and red LEDs on Raspberry Pi.
"""
import logging
import threading
import time
from typing import Optional

from app.utils.config import LED_PINS, IS_RASPBERRY_PI

logger = logging.getLogger(__name__)


# LED state machine: application state → LED behavior
LED_STATES = {
    'idle': 'all_off',
    'playing_tts': 'green_on',
    'recording': 'green_blink',
    'processing': 'orange_blink',
    'score_excellent': 'green_solid_3s',
    'score_good': 'orange_solid_3s',
    'score_poor': 'red_solid_3s',
    'error': 'red_rapid_blink',
}


class LEDService:
    """GPIO LED control for Raspberry Pi."""

    def __init__(self):
        self._gpio = None
        self._initialized = False
        self._pins = LED_PINS.copy()
        self._blink_threads: dict[str, threading.Thread] = {}
        self._blink_events: dict[str, threading.Event] = {}

    def initialize(self, pins: dict = None) -> bool:
        """
        Setup GPIO pins for LED control.

        Args:
            pins: {'green': 17, 'orange': 27, 'red': 22}

        Returns:
            True if successful
        """
        if pins:
            self._pins = pins

        if not IS_RASPBERRY_PI:
            logger.info("Not on Raspberry Pi — LED service running in simulation mode.")
            self._initialized = True
            return True

        try:
            import RPi.GPIO as GPIO
            self._gpio = GPIO

            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            for color, pin in self._pins.items():
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)

            self._initialized = True
            logger.info("GPIO initialized. Pins: %s", self._pins)
            return True

        except ImportError:
            logger.warning("RPi.GPIO not available. LED service in simulation mode.")
            self._initialized = True
            return True
        except Exception as e:
            logger.error("GPIO initialization failed: %s", e)
            self._initialized = False
            return False

    @property
    def is_available(self) -> bool:
        return self._initialized

    def set_led(self, color: str, state: str, duration: float = None):
        """
        Control LED state.

        Args:
            color: 'green', 'orange', 'red', or 'all'
            state: 'on', 'off', 'blink'
            duration: For 'on' state, auto-off after N seconds
        """
        if not self._initialized:
            return

        colors = [color] if color != 'all' else list(self._pins.keys())

        for c in colors:
            # Stop any existing blink for this color
            self._stop_blink(c)

            if state == 'on':
                self._set_pin(c, True)
                if duration:
                    # Auto-off after duration
                    t = threading.Timer(duration, self._set_pin, args=(c, False))
                    t.daemon = True
                    t.start()

            elif state == 'off':
                self._set_pin(c, False)

            elif state == 'blink':
                self._start_blink(c, on_time=0.5, off_time=0.5)

        logger.debug("LED %s → %s (duration=%s)", color, state, duration)

    def set_state(self, app_state: str):
        """
        Set LED based on application state.

        Args:
            app_state: Key from LED_STATES dict
        """
        behavior = LED_STATES.get(app_state, 'all_off')

        # Turn off all first
        self.all_off()

        if behavior == 'all_off':
            pass
        elif behavior == 'green_on':
            self.set_led('green', 'on')
        elif behavior == 'green_blink':
            self.set_led('green', 'blink')
        elif behavior == 'orange_blink':
            self.set_led('orange', 'blink')
        elif behavior == 'green_solid_3s':
            self.set_led('green', 'on', duration=3.0)
        elif behavior == 'orange_solid_3s':
            self.set_led('orange', 'on', duration=3.0)
        elif behavior == 'red_solid_3s':
            self.set_led('red', 'on', duration=3.0)
        elif behavior == 'red_rapid_blink':
            self._start_blink('red', on_time=0.2, off_time=0.2)

    def all_off(self):
        """Turn off all LEDs."""
        for color in self._pins:
            self._stop_blink(color)
            self._set_pin(color, False)

    def _set_pin(self, color: str, high: bool):
        """Set a GPIO pin high or low."""
        if self._gpio and color in self._pins:
            try:
                pin = self._pins[color]
                self._gpio.output(pin, self._gpio.HIGH if high else self._gpio.LOW)
            except Exception:
                pass
        # In simulation mode, just log
        elif not IS_RASPBERRY_PI:
            logger.debug("SIM LED %s: %s", color, "ON" if high else "OFF")

    def _start_blink(self, color: str, on_time: float = 0.5, off_time: float = 0.5):
        """Start blinking an LED in a background thread."""
        self._stop_blink(color)
        stop_event = threading.Event()
        self._blink_events[color] = stop_event

        def _blink():
            while not stop_event.is_set():
                self._set_pin(color, True)
                if stop_event.wait(on_time):
                    break
                self._set_pin(color, False)
                if stop_event.wait(off_time):
                    break
            self._set_pin(color, False)

        t = threading.Thread(target=_blink, daemon=True)
        self._blink_threads[color] = t
        t.start()

    def _stop_blink(self, color: str):
        """Stop blinking for a given color."""
        event = self._blink_events.pop(color, None)
        if event:
            event.set()
        thread = self._blink_threads.pop(color, None)
        if thread and thread.is_alive():
            thread.join(timeout=1.0)

    def cleanup(self):
        """Release GPIO resources."""
        self.all_off()
        if self._gpio:
            try:
                self._gpio.cleanup()
            except Exception:
                pass
        self._initialized = False
        logger.info("GPIO cleaned up.")

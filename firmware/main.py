"""
Simon Says memory game
Raspberry Pi Pico (RP2040) on a custom 2-layer PCB

Hardware mapping (matches JacobSimonSays.SchDoc):
    GP0, GP1, GP2, GP3      -> SW1-SW4, TS-1109 tactile switches to GND
                               Internal pull-ups are enabled, so a pressed
                               button reads 0. There are no external pull-up
                               resistors on the board.
    GP28, GP27, GP26, GP22  -> LEDs through 100 ohm series resistors

Gameplay:
    Each round appends one new random step to the sequence, plays the whole
    sequence back, then waits for the player to repeat it. A wrong entry
    triggers a failure animation and resets the sequence.
"""

from machine import Pin
import os
import random
import time

BUTTON_PINS = (0, 1, 2, 3)
LED_PINS = (28, 27, 26, 22)

FLASH_MS = 300          # how long each LED stays lit during playback
GAP_MS = 200            # dark time between playback steps
PRESS_FEEDBACK_MS = 150 # how long the LED lights when the player presses
DEBOUNCE_MS = 20        # settling time after a contact change
START_DELAY_MS = 700    # pause before a sequence is played back


def seed_random():
    """
    Seed the PRNG from hardware entropy.

    Without this, MicroPython may start from the same internal state on every
    power cycle, which makes the game deal an identical sequence every time
    the board is plugged in. os.urandom() on the RP2040 draws from the ring
    oscillator, so each boot starts somewhere different.
    """
    seed_bytes = os.urandom(4)
    random.seed(int.from_bytes(seed_bytes, "big"))


def wait_for_release(button):
    """
    Block until the button is let go, then let the contact settle.

    This is what stops a single held press from registering as several
    entries. Polling the button level alone counts one press per loop
    iteration for as long as it is held down.
    """
    while button.value() == 0:
        time.sleep_ms(DEBOUNCE_MS)
    time.sleep_ms(DEBOUNCE_MS)


def flash(led, on_ms=FLASH_MS, off_ms=GAP_MS):
    led.on()
    time.sleep_ms(on_ms)
    led.off()
    time.sleep_ms(off_ms)


def play_sequence(sequence, leds):
    time.sleep_ms(START_DELAY_MS)
    for index in sequence:
        flash(leds[index])


def read_player_press(buttons, leds):
    """
    Wait for one button press and return its index.

    The LED for the pressed button is lit briefly so the player gets
    confirmation on every entry rather than only at the end of the round.
    """
    while True:
        for index, button in enumerate(buttons):
            if button.value() == 0:
                wait_for_release(button)
                flash(leds[index], PRESS_FEEDBACK_MS, 0)
                return index
        time.sleep_ms(5)


def play_failure_animation(leds):
    for led in leds:
        flash(led, 150, 0)
    for led in reversed(leds):
        flash(led, 150, 0)
    time.sleep_ms(1000)


def main():
    buttons = [Pin(pin, Pin.IN, Pin.PULL_UP) for pin in BUTTON_PINS]
    leds = [Pin(pin, Pin.OUT) for pin in LED_PINS]

    seed_random()
    sequence = []

    while True:
        sequence.append(random.randrange(len(leds)))
        play_sequence(sequence, leds)

        for expected in sequence:
            if read_player_press(buttons, leds) != expected:
                print("Wrong. Sequence length reached:", len(sequence) - 1)
                play_failure_animation(leds)
                sequence = []
                break
        else:
            print("Correct. Sequence length:", len(sequence))


main()

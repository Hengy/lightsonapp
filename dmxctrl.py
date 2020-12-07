import multiprocessing

import opc

import os

import sys

import time
import datetime

import json

import functools

import env_config

import RPi.GPIO as GPIO

import math

import random

import signal

numLEDs = env_config.NUM_LEDS
client = opc.Client(env_config.OPC_ADDR)

if env_config.RELAY_LOGIC_INV:
    RELAY_LOGIC_ON = GPIO.LOW
    RELAY_LOGIC_OFF = GPIO.HIGH
else:
    RELAY_LOGIC_ON = GPIO.HIGH
    RELAY_LOGIC_OFF = GPIO.LOW

# converts HSV to RGB values; h = 0..359, s,v = 0..1
def HSVtoRGB(h, s, v):
    if s == 0.0: v*=255; return (v, v, v)
    i = int(h*6.) # XXX assume int() truncates!
    f = (h*6.)-i; p,q,t = int(255*(v*(1.-s))), int(255*(v*(1.-s*f))), int(255*(v*(1.-s*(1.-f)))); v*=255; i%=6
    if i == 0: return (v, t, p)
    if i == 1: return (q, v, p)
    if i == 2: return (p, v, t)
    if i == 3: return (p, q, v)
    if i == 4: return (t, p, v)
    if i == 5: return (v, p, q)

LIB_GREEN_R = 150
LIB_GREEN_G = 202
LIB_GREEN_B = 80

LIB_BLUE_R = 0
LIB_BLUE_G = 171
LIB_BLUE_B = 232

LIB_PURPLE_R = 87
LIB_PURPLE_G = 52
LIB_PURPLE_B = 148

# -----------------------------------------------------
# Check if it is within Lights On time
# returns True if it is between TIME_ON and TIME_OFF
# -----------------------------------------------------
def check_in_time():
  in_time = False
  hour_now = datetime.datetime.now().hour
  minute_now = datetime.datetime.now().minute
  if hour_now >= env_config.TIME_ON_HOUR and minute_now >= env_config.TIME_ON_MIN:
    if hour_now <= env_config.TIME_OFF_HOUR and minute_now <= env_config.TIME_OFF_MIN:
      in_time = True

  return in_time

def signal_handler(signal, frame):
    GPIO.cleanup()
    print("exiting DMX...")
    sys.exit(0)

class LEDController():
    def __init__(self):

        print("Initializing new DMX light controller")

        signal.signal(signal.SIGINT, signal_handler)

        random.seed(time.time())

        GPIO.setmode(GPIO.BOARD)

        for i in range(len(env_config.RELAY_PINS)):
            GPIO.setup(env_config.RELAY_PINS[i], GPIO.OUT)
            GPIO.output(env_config.RELAY_PINS[i], RELAY_LOGIC_OFF)

        # state machine variables
        # ----------------------------------------------------------------------
        # state: 0 = IDLE; 1 = BLANK; 2 = STREAMING; > 3 = LED Effect modes
        self._state = 3
        
        # message polling
        self.poll_period = 10 # polling period in ms

        # effect delay time
        self.effect_delay = 500 # ms

        # routine1
        self.state3_toggle = False

        # ----------------------------------------------------------------------

        print("DMX Controller initialized")

    # led controller state machine
    def run(self, conn):
        print("DMX Process ID: ", os.getpid())

        msg = {"CMD":None}

        time_now = int(round(time.time() * 1000)) # time now
        time_prev_poll = 0

        time_prev_pixel_update = 0

        while msg["CMD"] != "END":
        # state machine beginning -------------------------------------------------------
            time_now = int(round(time.time() * 1000)) # time now

            if time_now - time_prev_poll >= self.poll_period:

                time_prev_poll = int(round(time.time() * 1000))
                if conn.poll():
                    jsonmsg = conn.recv()
                    msg = json.loads(jsonmsg)
                    if msg["CMD"] == "ROUTINE1":
                        self.effect_delay = 500
                        self._state = 3
                    elif msg["CMD"] == "IDLE":
                        self.effect_delay = 50
                        print("idling LEDs...")
                        self._state = 0
                    else:
                        self.effect_delay = 50
                        print("idling LEDs...")
                        self._state = 0

            if time_now - time_prev_pixel_update >= self.effect_delay:
                time_prev_pixel_update = int(round(time.time() * 1000)) # time now
                if self._state == 0:
                    self.idle()
                elif self._state == 1:
                    self.idle()
                elif self._state == 3:
                    self.routine1()
                else:
                    self.idle()

        # state machine end ------------------------------------------------------------
        print("Ending child...")
        exit()

    # idle LED routines
    def idle(self):
        self.blank()

    # blank all LEDs
    def blank(self):
        for i in range(len(env_config.RELAY_PINS)):
            GPIO.output(env_config.RELAY_PINS[i], RELAY_LOGIC_OFF)

    # fades in to color; color switches to next in rainbow
    def routine1(self):

        if self.state3_toggle:
            self.state3_toggle = False
        else:
            self.state3_toggle = True

        for i in range(len(env_config.RELAY_PINS)):

            if self.state3_toggle:
                GPIO.output(env_config.RELAY_PINS[i], RELAY_LOGIC_ON)
            else:
                GPIO.output(env_config.RELAY_PINS[i], RELAY_LOGIC_OFF)

  
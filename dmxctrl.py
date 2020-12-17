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
  if hour_now >= env_config.TIME_ON_HOUR:
    if hour_now <= env_config.TIME_OFF_HOUR:
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

        GPIO.setup(env_config.RELAY_PIN_IDLE, GPIO.OUT)
        GPIO.output(env_config.RELAY_PIN_IDLE, RELAY_LOGIC_OFF)

        GPIO.setup(env_config.RELAY_PIN_OFF, GPIO.OUT)
        GPIO.output(env_config.RELAY_PIN_OFF, RELAY_LOGIC_OFF)

        # state machine variables
        # ----------------------------------------------------------------------
        # state: 0 = IDLE; 1 = BLANK; 2 = STREAMING; > 3 = LED Effect modes
        self._prev_state = -1
        self._state = 1
        
        # message polling
        self.poll_period = 10 # polling period in ms

        # routine1
        self.state3_states = [0,0,0] # R,G,B

        # ----------------------------------------------------------------------

        if check_in_time():  # if it IS time to display
            self._state = 0 # idle
            self.idle()
        else:
            self.blank()

        print("DMX Controller initialized")

    # led controller state machine
    def run(self, conn):
        print("DMX Process ID: ", os.getpid())

        msg = {"CMD":None}

        time_now = int(round(time.time() * 1000)) # time now
        time_prev_poll = 0

        while msg["CMD"] != "END":
        # state machine beginning -------------------------------------------------------
            time_now = int(round(time.time() * 1000)) # time now

            # if check_in_time():  # if it IS time to display
            #     self._state = 0 # idle

            if time_now - time_prev_poll >= self.poll_period:

                time_prev_poll = int(round(time.time() * 1000))
                if conn.poll():
                    jsonmsg = conn.recv()
                    msg = json.loads(jsonmsg)
                    if msg["CMD"] == "ROUTINE1":
                        self._state = 3
                    elif msg["CMD"] == "ROUTINE2":
                        self._state = 4
                    elif msg["CMD"] == "ROUTINE3":
                        self._state = 5
                    elif msg["CMD"] == "ROUTINE4":
                        self._state = 6
                    elif msg["CMD"] == "ROUTINE5":
                        self._state = 7
                    elif msg["CMD"] == "ROUTINE6":
                        self._state = 8
                    elif msg["CMD"] == "RANDOM":
                        self._state = random.choice([3,4,5,6,7,8])
                        while self._state == self._prev_state:
                            self._state = random.choice([3,4,5,6,7,8])
                    elif msg["CMD"] == "IDLE":
                        self._state = 0

            if not check_in_time():  # if it is NOT time to display
                self._state = 1 # blank

            # print("state: ", self._state, " prev state: ", self._prev_state)

            if self._state == 0:
                self.idle()
            elif self._state == 1:
                self.blank()
            elif self._state == 3:
                self.routine(1)
            elif self._state == 4:
                self.routine(2)
            elif self._state == 5:
                self.routine(3)
            elif self._state == 6:
                self.routine(4)
            elif self._state == 7:
                self.routine(5)
            elif self._state == 8:
                self.routine(6)
            else:
                self.idle()

            if self._prev_state != self._state:
                print("state: ", self._state, " prev state: ", self._prev_state)

        # state machine end ------------------------------------------------------------
        print("Ending child...")
        exit()

    # idle LED routines
    def idle(self):
        if self._prev_state != 0:
            GPIO.output(env_config.RELAY_PIN_IDLE, RELAY_LOGIC_ON)
            time.sleep(env_config.RELAY_PIN_MOM_TIME)
            print("switched to idle @ ", time.time())
            GPIO.output(env_config.RELAY_PIN_IDLE, RELAY_LOGIC_OFF)
            self._prev_state = 0

    # blank all LEDs
    def blank(self):
        if self._prev_state != 1:
            GPIO.output(env_config.RELAY_PIN_OFF, RELAY_LOGIC_ON)
            time.sleep(env_config.RELAY_PIN_MOM_TIME)
            print("switched to blank @ ", time.time())
            GPIO.output(env_config.RELAY_PIN_OFF, RELAY_LOGIC_OFF)
            self._prev_state = 1    

    # chooses one of 6 combinations
    def routine(self, num):
        if self._prev_state != (num + 2):
            GPIO.output(env_config.RELAY_PINS[num-1], RELAY_LOGIC_ON)
            time.sleep(env_config.RELAY_PIN_MOM_TIME)
            print("switching to routine ", num, " @ ", time.time())
            GPIO.output(env_config.RELAY_PINS[num-1], RELAY_LOGIC_OFF)
            self._prev_state = num + 2
  
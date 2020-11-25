import multiprocessing

import opc

import os

import time

import json

import functools

import env_config

numLEDs = env_config.NUM_LEDS
client = opc.Client(env_config.OPC_ADDR)

class LEDController():
    def __init__(self):

        # pixel buffer
        self.pixels = [(0,0,0)] * numLEDs

        # state machine variables
        # ----------------------------------------------------------------------
        # state: 0 = IDLE; 1 = BLANK; 2 = STREAMING; > 3 = LED Effect modes
        self._state = 0
        
        # message polling
        self.poll_period = 10 # polling period in ms

        # effect delay time
        self.effect_delay = 20 # ms

        # 
        self.state3_color = 0
        self.state3_brightness = 0
        self.state3_step = 1
        # ----------------------------------------------------------------------

        print("LED Controller initialized")

    # led controller state machine
    def run(self, conn):
        print("Fadecandy Process ID: ", os.getpid())

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
                    if msg["CMD"] == "LED":
                        print("changing state...")
                        self._state = 3
                    elif msg["CMD"] == "DARK":
                        print("turning off LEDs...")
                        self._state = 1
                    elif msg["CMD"] == "IDLE":
                        print("idling LEDs...")
                        self._state = 0
                    else:
                        print("idling LEDs...")
                        self._state = 0

            if time_now - time_prev_pixel_update >= self.effect_delay:
                time_prev_pixel_update = int(round(time.time() * 1000)) # time now
                if self._state == 0:
                    self.idle_leds()
                elif self._state == 1:
                    self.blank_leds()
                elif self._state == 3:
                    self.rgb_leds()
                else:
                    self.idle_leds()

        # state machine end ------------------------------------------------------------
        self.blank_leds()
        print("Ending child...")
        exit()

    # idle LED routines
    def idle_leds(self):
        self.pixels = [(100,31,143)] * numLEDs
        client.put_pixels(self.pixels)

    # blank all LEDs
    def blank_leds(self):
        self.pixels = [(0,0,0)] * numLEDs
        client.put_pixels(self.pixels)

    # RGB switch routine
    def rgb_leds(self):
        
        self.pixels = [(0,0,0)] * numLEDs

        k = self.state3_brightness
        if k > 255:
            k = 255

        if self.state3_color == 0:
            self.pixels = [(k,0,0)] * numLEDs
        elif self.state3_color == 1:
            self.pixels = [(k,k*0.3,0)] * numLEDs
        elif self.state3_color == 2:
            self.pixels = [(k,k*0.9,0)] * numLEDs
        elif self.state3_color == 3:
            self.pixels = [(0,k,0)] * numLEDs
        elif self.state3_color == 4:
            self.pixels = [(0,k,k)] * numLEDs
        elif self.state3_color == 5:
            self.pixels = [(0,0,k)] * numLEDs
        else:
            self.pixels = [(k,0,k)] * numLEDs
        client.put_pixels(self.pixels)

        self.state3_brightness += self.state3_step
        if self.state3_brightness >= 400:
            self.state3_brightness = 0
            self.state3_color += 1
            if self.state3_color >= 7:
                self.state3_color = 0
        

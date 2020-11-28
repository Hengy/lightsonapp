import multiprocessing

import opc

import os

import time

import json

import functools

import env_config

import RPi.GPIO

import math

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

        # Rainbow Fade In
        self.state3_color = 0
        self.state3_brightness = 0
        self.state3_step = 1

        # Rainbow
        self.state4_color = 0
        self.state4_step = 0.003

        # Chase
        self.state5_position = 0
        self.state5_color = 0
        self.state5_step = 0.05
        self.state5_speed = 3

        # theatre chase
        self.state6_position = 9
        self.state6_brightness = 255
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
                    if msg["CMD"] == "FADEIN":
                        self.effect_delay = 20
                        self.state3_color = 0
                        self._state = 3
                    elif msg["CMD"] == "RAINBOW":
                        self.effect_delay = 20
                        self._state = 4
                    elif msg["CMD"] == "CHASE":
                        self.effect_delay = 20
                        self._state = 5
                    elif msg["CMD"] == "THEATRE":
                        self.effect_delay = 40
                        self._state = 6
                    elif msg["CMD"] == "DARK":
                        self.effect_delay = 20
                        print("turning off LEDs...")
                        self._state = 1
                    elif msg["CMD"] == "IDLE":
                        self.effect_delay = 20
                        print("idling LEDs...")
                        self._state = 0
                    else:
                        self.effect_delay = 20
                        print("idling LEDs...")
                        self._state = 0

            if time_now - time_prev_pixel_update >= self.effect_delay:
                time_prev_pixel_update = int(round(time.time() * 1000)) # time now
                if self._state == 0:
                    self.idle_leds()
                elif self._state == 1:
                    self.blank_leds()
                elif self._state == 3:
                    self.rainbowfadein()
                elif self._state == 4:
                    self.rainbow()
                elif self._state == 5:
                    self.chase()
                elif self._state == 6:
                    self.theatre_chase()
                else:
                    self.idle_leds()

        # state machine end ------------------------------------------------------------
        self.blank_leds()
        print("Ending child...")
        exit()

    # converts HSV to RGB values; h = 0..359, s,v = 0..1
    def HSVtoRGB(self, h, s, v):
        if s == 0.0: v*=255; return (v, v, v)
        i = int(h*6.) # XXX assume int() truncates!
        f = (h*6.)-i; p,q,t = int(255*(v*(1.-s))), int(255*(v*(1.-s*f))), int(255*(v*(1.-s*(1.-f)))); v*=255; i%=6
        if i == 0: return (v, t, p)
        if i == 1: return (q, v, p)
        if i == 2: return (p, v, t)
        if i == 3: return (p, q, v)
        if i == 4: return (t, p, v)
        if i == 5: return (v, p, q)

    # idle LED routines
    def idle_leds(self):
        self.pixels = [(100,31,143)] * numLEDs
        client.put_pixels(self.pixels)

    # blank all LEDs
    def blank_leds(self):
        self.pixels = [(0,0,0)] * numLEDs
        client.put_pixels(self.pixels)

    # fades in to color; color switches to next in rainbow
    def rainbowfadein(self):
        
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

    # goes through rainbow
    def rainbow(self):

        new_color = self.HSVtoRGB(self.state4_color,1,1)
        self.state4_color += self.state4_step
        if self.state4_color > 0.9999:
            self.state4_color = 0

        self.pixels = [new_color] * numLEDs

        client.put_pixels(self.pixels)

    # 5 pixels chase entire length of strip
    def chase(self):

        self.pixels = [(0,0,0)] * numLEDs

        new_color = self.HSVtoRGB(self.state5_color,1,1)

        for i in range(12):
            self.pixels[self.state5_position + i] = new_color

        self.state5_position += self.state5_speed
        if self.state5_position > (numLEDs - 12):
            self.state5_position = 0
            self.state5_color += self.state5_step

        client.put_pixels(self.pixels)

    # theatre chase
    def theatre_chase(self):

        val = self.state6_brightness

        self.pixels = [(0,0,0)] * numLEDs

        for i in range(numLEDs - 5):
            if (i+self.state6_position) % 10 == 0:
                self.pixels[i+5] = (val,0,0)
                self.pixels[i+4] = (val*0.8,0,0)
                self.pixels[i+3] = (val*0.4,0,0)
                self.pixels[i+2] = (val*0.3,0,0)
                self.pixels[i+1] = (val*0.2,0,0)
                self.pixels[i] = (val*0.1,0,0)

        self.state6_position -= 1
        if self.state6_position == 0:
            self.state6_position = 9

        client.put_pixels(self.pixels)

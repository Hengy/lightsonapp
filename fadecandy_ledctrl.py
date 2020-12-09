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

numLEDs = 1
client = opc.Client(env_config.OPC_ADDR)

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
    print("exiting LEDs...")
    sys.exit(0)

class LEDController():
    def __init__(self):

        global numLEDs

        print("Local IP Address: ", env_config.get_self_ip())

        print("Now env_config SELF_IP is: ", env_config.SELF_IP)

        env_config.config_leds()

        numLEDs = env_config.NUM_LEDS

        print("Upper Pane: ", env_config.WIN_UPPER_PANE)
        print("Display type (0 = LEDs, 1 = DMX/Relays): ", env_config.PI_DISPLAY_TYPE)
        print("LEDs: ", env_config.NUM_LEDS)

        print("Initializing new fadecandy LED controller")

        signal.signal(signal.SIGINT, signal_handler)

        random.seed(time.time())

        GPIO.setmode(GPIO.BOARD)

        self.power_pin =env_config.PSU_PIN
        self.last_power_toggle_time = time.time()

        GPIO.setup(self.power_pin, GPIO.OUT)
        GPIO.output(self.power_pin, GPIO.HIGH)

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

        # idle
        self.idle_mode = 4
        self.idle_mode_max = 4
        self.idle_mode_time = 0
        self.idle_change_time = 0
        self.idle_color = 0
        self.idle_brightness = 0.7
        self.idle_step = 0.0002
        self.idle_build_dir = True
        self.idle_build_array = []
        self.idle_build_array2 = []
        self.idle_build_max_delay = 1500
        self.idle_build_chunk_min = 6
        self.idle_build_chunk_max = 12
        self.idle_build_speed = 0.87

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
        self.state5_speed = 2

        # theatre chase
        self.state6_position = 9
        self.state6_brightness = 255

        # Dual Chase
        self.state7_position = 0
        self.state7_position2 = int(numLEDs/2) + 12
        self.state7_color = self.state5_step
        self.state7_color2 = 0

        # Triple Chase
        self.state8_position = 0
        self.state8_position2 = int(numLEDs/3) + 8
        self.state8_position3 = int((numLEDs/3) * 2) + 16
        self.state8_color = self.state5_step
        self.state8_color2 = 0
        self.state8_color3 = 1 - self.state5_step

        # build up/down
        self.state9_dir = True
        self.state9_array = []
        self.state9_array2 = []
        self.state9_max_delay = 1500
        self.state9_chunk_min = 10
        self.state9_chunk_max = 18
        self.state9_speed = 0.87
        self.state9_color = 0
        self.state9_step = 0.055
        # ----------------------------------------------------------------------

        print("LED Controller initialized")

    def adj_brightness(self):
        if env_config.LED_POWER_LIMIT:
            for i in range(len(self.pixels)):
                new_pixel = (self.pixels[i][0]*env_config.LED_POWER_SCALE,self.pixels[i][1]*env_config.LED_POWER_SCALE,self.pixels[i][2]*env_config.LED_POWER_SCALE)
                self.pixels[i] = new_pixel

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

                in_time = check_in_time()
                if in_time and (time_now - self.last_power_toggle_time) > 30:
                    GPIO.output(self.power_pin, GPIO.LOW)
                    self.last_power_toggle_time = time.time()
                else:
                    GPIO.output(self.power_pin, GPIO.HIGH)
                    self.last_power_toggle_time = time.time()

                time_prev_poll = int(round(time.time() * 1000))
                if conn.poll():
                    jsonmsg = conn.recv()
                    msg = json.loads(jsonmsg)
                    if msg["CMD"] == "FADEIN":
                        self.effect_delay = 20
                        self.state3_color = random.randint(0,6)
                        self._state = 3
                    elif msg["CMD"] == "RAINBOW":
                        self.effect_delay = 80
                        self._state = 4
                    elif msg["CMD"] == "CHASE":
                        self.effect_delay = 25
                        self._state = 5
                    elif msg["CMD"] == "THEATRE":
                        self.effect_delay = 40
                        self._state = 6
                    elif msg["CMD"] == "DUALCHASE":
                        self.effect_delay = 25
                        self._state = 7
                    elif msg["CMD"] == "TRIPLECHASE":
                        self.effect_delay = 25
                        self._state = 8
                    elif msg["CMD"] == "BUILDUPDOWN":
                        self.pixels = [(0,0,0)] * numLEDs
                        self.effect_delay = self.state9_max_delay

                        self.state9_array = []

                        # build random 'chunk' list
                        done = False
                        pos = 0
                        while not done:
                            end = pos + random.randint(self.state9_chunk_min,self.state9_chunk_max)
                            if end >= numLEDs:
                                end = numLEDs - 1
                            self.state9_array.append((pos, end))
                            if end != numLEDs - 1:
                                pos = end
                            else:
                                done = True

                        self._state = 9
                    elif msg["CMD"] == "DARK":
                        self.effect_delay = 20
                        print("turning off LEDs...")
                        self._state = 1
                    elif msg["CMD"] == "STREAM":
                        if env_config.LED_POWER_LIMIT:
                            new_color = HSVtoRGB(msg["Data"][0]/360, msg["Data"][1]/100, (msg["Data"][2]/100)*env_config.LED_POWER_SCALE)
                        else:
                            new_color = HSVtoRGB(msg["Data"][0]/360, msg["Data"][1]/100, msg["Data"][2]/100)
                        self.pixels = [new_color] * numLEDs
                        self._state = 2
                    elif msg["CMD"] == "IDLE":
                        self.pixels = [(0,0,0)] * numLEDs
                        self.effect_delay = 20
                        print("idling LEDs...")
                        self._state = 0
                    else:
                        self.pixels = [(0,0,0)] * numLEDs
                        self.effect_delay = 20
                        print("idling LEDs...")
                        self._state = 0

            if time_now - time_prev_pixel_update >= self.effect_delay:
                time_prev_pixel_update = int(round(time.time() * 1000)) # time now
                if self._state == 0:
                    self.idle_leds()
                elif self._state == 2:
                    pass  
                elif self._state == 1:
                    self.blank_leds()
                elif self._state == 3:
                    self.rainbowfadein()
                    self.adj_brightness()
                elif self._state == 4:
                    self.rainbow()
                    self.adj_brightness()
                elif self._state == 5:
                    self.chase()
                elif self._state == 6:
                    self.theatre_chase()
                elif self._state == 7:
                    self.dualchase()
                elif self._state == 8:
                    self.triplechase()
                elif self._state == 9:
                    self.build_up_down()
                else:
                    self.idle_leds()

            if not check_in_time():
                self.pixels = [(0,0,0)] * numLEDs
            client.put_pixels(self.pixels)

        # state machine end ------------------------------------------------------------
        self.blank_leds()
        print("Ending child...")
        exit()

    # idle LED routines
    def idle_leds(self):

        if self.idle_change_time == 0:
            self.idle_change_time = time.time() + env_config.IDLE_COLOR_CHANGE_TIME + random.randint(0,10) - 5
            self.idle_mode_time = time.time() + env_config.IDLE_MODE_CHANGE_TIME
            self.idle_color = random.randint(0,2)
            self.idle_brightness = random.randint(55,76)/100

            if self.idle_mode == 4:
                self.effect_delay = self.idle_build_max_delay
                self.idle_color = random.choice([86/360,196/360,280/360,86/360,196/360,280/360])
                self.idle_build_array = []

                # build random 'chunk' list
                done = False
                pos = 0
                while not done:
                    end = pos + random.randint(self.idle_build_chunk_min,self.idle_build_chunk_max)
                    if end >= numLEDs:
                        end = numLEDs - 1
                    self.idle_build_array.append((pos, end))
                    if end != numLEDs - 1:
                        pos = end
                    else:
                        done = True

            if self.idle_mode == 2:
                self.pixels = [(0,0,0)] * numLEDs

        if self.idle_mode_time <= time.time():
            self.idle_mode_time = time.time() + env_config.IDLE_MODE_CHANGE_TIME
            self.idle_mode += 1
            
            if self.idle_mode > self.idle_mode_max:
                self.idle_mode = 1
            # print("MODE: ", self.idle_mode)

            if self.idle_mode == 1:
                self.idle_mode_time = time.time() + env_config.IDLE_MODE_CHANGE_TIME
            if  self.idle_mode == 2:
                self.pixels = [(0,0,0)] * numLEDs
            elif self.idle_mode == 4:

                self.pixels = [(0,0,0)] * numLEDs
                self.effect_delay = self.idle_build_max_delay
                self.idle_color = random.choice([86/360,196/360,280/360,86/360,196/360,280/360,-1])

                self.idle_build_array = []

                # build random 'chunk' list
                done = False
                pos = 0
                while not done:
                    end = pos + random.randint(self.idle_build_chunk_min,self.idle_build_chunk_max)
                    if end >= numLEDs:
                        end = numLEDs - 1
                    self.idle_build_array.append((pos, end))
                    if end != numLEDs - 1:
                        pos = end
                    else:
                        done = True

            elif self.idle_mode == 3:
                self.idle_color = env_config.IDLE_SYNC_OFFSET01
        
        if self.idle_mode == 1:
            self.idle_static()
        elif self.idle_mode == 2:
            self.effect_delay = random.choice([2000,2500,3000])
            self.idle_rotate()
        elif self.idle_mode == 3:
            self.idle_rainbow()
            self.adj_brightness()
        elif self.idle_mode == 4:
            self.idle_build()
        elif self.idle_mode == 5:
            self.idle_breath()
        else:
            self.pixels = [(100,31,143)] * numLEDs

        
    def idle_static(self):
        
        if self.idle_change_time <= time.time():

            new_color = math.trunc(random.randint(0,299) / 100)
            while new_color == self.idle_color:
                new_color = math.trunc(random.randint(0,299) / 100)

            self.idle_color = new_color

            if self.idle_color == 2:
                self.idle_brightness = random.randint(65,85)/100
            else:
                self.idle_brightness = random.randint(55,75)/100

            self.idle_change_time = time.time() + env_config.IDLE_COLOR_CHANGE_TIME + random.randint(0,10) - 5

        if self.idle_color == 0:
            new_color = (LIB_BLUE_R*self.idle_brightness,LIB_BLUE_G*self.idle_brightness,LIB_BLUE_B*self.idle_brightness)
            self.pixels = [new_color] * numLEDs
        elif self.idle_color == 1:
            new_color = (LIB_GREEN_R*self.idle_brightness,LIB_GREEN_G*self.idle_brightness,LIB_GREEN_B*self.idle_brightness)
            self.pixels = [new_color] * numLEDs
        else:
            new_color = (LIB_PURPLE_R*self.idle_brightness,LIB_PURPLE_G*self.idle_brightness,LIB_PURPLE_B*self.idle_brightness)
            self.pixels = [new_color] * numLEDs

    def idle_rotate(self):
        if env_config.WIN_UPPER_PANE:
            pane = random.randint(0,3)
        else:
            pane = random.randint(0,3)
        new_color_index = random.choice([-1,86/360,196/360,280/360,-1,86/360,196/360,280/360])
        if new_color_index != -1:
            new_color = HSVtoRGB(new_color_index,1,0.7)
        else:
            new_color = (0,0,0)

        # if pane == 0:
        #     for i in range(env_config.WIN_PANE1[0],env_config.WIN_PANE1[1]):
        #         self.pixels[i] = new_color
        # elif pane == 1:
        #     for i in range(env_config.WIN_PANE2[0],env_config.WIN_PANE2[1]):
        #         self.pixels[i] = new_color
        # elif pane == 2:
        #     for i in range(env_config.WIN_PANE3[0],env_config.WIN_PANE3[1]):
        #         self.pixels[i] = new_color
        # else:
        #     for i in range(env_config.WIN_PANE4[0],env_config.WIN_PANE4[1]):
        #         self.pixels[i] = new_color

    def idle_rainbow(self):
        new_color = HSVtoRGB(self.idle_color,1,1)

        self.idle_color += self.idle_step
        if(self.idle_color >= 1.0):
            self.idle_color = 0

        self.pixels = [new_color] * numLEDs

    def idle_build(self):
        new_color = HSVtoRGB(self.idle_color,1,0.7)

        if self.idle_build_dir:
            pick = random.randint(0, len(self.idle_build_array)-1)
            if len(self.idle_build_array) > 0:
                section = self.idle_build_array.pop(pick)
                self.idle_build_array2.append(section)
                for i in range(section[0],section[1]):
                    self.pixels[i] = new_color
            if self.effect_delay > 80:
                self.effect_delay = self.effect_delay*self.idle_build_speed
        else:
            pick = random.randint(0, len(self.idle_build_array2)-1)
            if len(self.idle_build_array2) > 0:
                section = self.idle_build_array2.pop(pick)
                self.idle_build_array.append(section)
                for i in range(section[0],section[1]):
                    self.pixels[i] = (0,0,0)
            if self.effect_delay > 80:
                self.effect_delay = self.effect_delay*self.idle_build_speed

        if len(self.idle_build_array) == 0:
            self.idle_build_dir = False
            self.effect_delay = self.idle_build_max_delay
        if len(self.idle_build_array2) == 0:
            self.idle_build_dir = True
            self.effect_delay = self.idle_build_max_delay

            self.idle_build_array = []
            self.idle_color = random.choice([86/360,196/360,280/360,86/360,196/360,280/360])

            # build random 'chunk' list
            done = False
            pos = 0
            while not done:
                end = pos + random.randint(self.idle_build_chunk_min,self.idle_build_chunk_max)
                if end >= numLEDs:
                    end = numLEDs - 1
                self.idle_build_array.append((pos, end))
                if end != numLEDs - 1:
                    pos = end
                else:
                    done = True


    def idle_breath(self):
        self.pixels = [(0,0,0)] * numLEDs

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


        self.state3_brightness += self.state3_step
        if self.state3_brightness >= 400:
            self.state3_brightness = 0
            self.state3_color += 1
            if self.state3_color >= 7:
                self.state3_color = 0

    # goes through rainbow
    def rainbow(self):

        new_color = HSVtoRGB(self.state4_color,1,1)
        self.state4_color += self.state4_step
        if self.state4_color > 0.9999:
            self.state4_color = 0

        self.pixels = [new_color] * numLEDs



    # 5 pixels chase entire length of strip
    def chase(self):

        self.pixels = [(0,0,0)] * numLEDs

        for i in range(20):
            pos = self.state5_position + i
            if i < 14:
                new_color = HSVtoRGB(self.state5_color,1,(i/20))
            else:
                new_color = HSVtoRGB(self.state5_color,1,1)

            if pos > 0 and pos < numLEDs:
                self.pixels[pos] = new_color

        self.state5_position += self.state5_speed
        if self.state5_position > (numLEDs + 10):
            self.state5_position = -14
            self.state5_color += self.state5_step



    # 5 pixels chase entire length of strip
    def dualchase(self):

        self.pixels = [(0,0,0)] * numLEDs


        for i in range(12):
            pos = self.state7_position + i
            pos2 = self.state7_position2 + i

            if i < 9:
                new_color = HSVtoRGB(self.state7_color,1,(i/12))
                new_color2 = HSVtoRGB(self.state7_color2,1,(i/12))
            else:
                new_color = HSVtoRGB(self.state7_color,1,1)
                new_color2 = HSVtoRGB(self.state7_color2,1,1)
                
            if pos > 0 and pos < numLEDs:
                self.pixels[pos] = new_color

            if pos2 > 0 and pos2 < numLEDs:
                self.pixels[pos2] = new_color2

        self.state7_position += self.state5_speed
        if self.state7_position > (numLEDs + 10):
            self.state7_position = -10
            self.state7_color += self.state5_step * 2

        self.state7_position2 += self.state5_speed
        if self.state7_position2 > (numLEDs + 10):
            self.state7_position2 = -10
            self.state7_color2 += self.state5_step * 2



    # 5 pixels chase entire length of strip
    def triplechase(self):

        self.pixels = [(0,0,0)] * numLEDs


        for i in range(12):
            pos = self.state8_position + i
            pos2 = self.state8_position2 + i
            pos3 = self.state8_position3 + i

            if i < 9:
                new_color = HSVtoRGB(self.state8_color,1,(i/12))
                new_color2 = HSVtoRGB(self.state8_color2,1,(i/12))
                new_color3 = HSVtoRGB(self.state8_color3,1,(i/12))
            else:
                new_color = HSVtoRGB(self.state8_color,1,1)
                new_color2 = HSVtoRGB(self.state8_color2,1,1)
                new_color3 = HSVtoRGB(self.state8_color3,1,1)
                
            if pos > 0 and pos < numLEDs:
                self.pixels[pos] = new_color

            if pos2 > 0 and pos2 < numLEDs:
                self.pixels[pos2] = new_color2

            if pos3 > 0 and pos3 < numLEDs:
                self.pixels[pos3] = new_color3

        self.state8_position += self.state5_speed
        if self.state8_position > (numLEDs + 10):
            self.state8_position = -10
            self.state8_color += self.state5_step * 3

        self.state8_position2 += self.state5_speed
        if self.state8_position2 > (numLEDs + 10):
            self.state8_position2 = -10
            self.state8_color2 += self.state5_step * 3

        self.state8_position3 += self.state5_speed
        if self.state8_position3 > (numLEDs + 10):
            self.state8_position3 = -10
            self.state8_color3 += self.state5_step * 3

    # theatre chase
    def theatre_chase(self):

        val = self.state6_brightness

        self.pixels = [(0,0,0)] * numLEDs

        for i in range(numLEDs - 6):
            if (i+self.state6_position) % 12 == 0:
                self.pixels[i+6] = (val,0,0)
                self.pixels[i+5] = (val,0,0)
                self.pixels[i+4] = (val*0.8,0,0)
                self.pixels[i+3] = (val*0.6,0,0)
                self.pixels[i+2] = (val*0.4,0,0)
                self.pixels[i+1] = (val*0.2,0,0)
                self.pixels[i] = (val*0.1,0,0)

        self.state6_position -= 1
        if self.state6_position == 0:
            self.state6_position = 11



    # Build up/down
    def build_up_down(self):
        new_color = HSVtoRGB(self.state9_color,1,0.7)

        if self.state9_dir:
            pick = random.randint(0, len(self.state9_array)-1)
            if len(self.state9_array) > 0:
                section = self.state9_array.pop(pick)
                self.state9_array2.append(section)
                for i in range(section[0],section[1]):
                    self.pixels[i] = new_color
            if self.effect_delay > 80:
                self.effect_delay = self.effect_delay*self.state9_speed
        else:
            pick = random.randint(0, len(self.state9_array2)-1)
            if len(self.state9_array2) > 0:
                section = self.state9_array2.pop(pick)
                self.state9_array.append(section)
                for i in range(section[0],section[1]):
                    self.pixels[i] = (0,0,0)
            if self.effect_delay > 80:
                self.effect_delay = self.effect_delay*self.state9_speed

        if len(self.state9_array) == 0:
            self.state9_dir = False
            self.effect_delay = self.state9_max_delay
        if len(self.state9_array2) == 0:
            self.state9_dir = True
            self.effect_delay = self.state9_max_delay

            self.state9_array = []
            self.state9_color += self.state9_step
            if self.state9_color > 1.0:
                self.state9_color = 0

            # build random 'chunk' list
            done = False
            pos = 0
            while not done:
                end = pos + random.randint(self.state9_chunk_min,self.state9_chunk_max)
                if end >= numLEDs:
                    end = numLEDs - 1
                self.state9_array.append((pos, end))
                if end != numLEDs - 1:
                    pos = end
                else:
                    done = True


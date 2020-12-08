
#------------------------------------------------------
# FLASK APP
#------------------------------------------------------

# Matt H Dev
SELF_IP =  "192.168.0.41"  # set to static IP address of Raspberry Pi
SELF_PORT = ":5000"
# SELF_PORT = ""

# SPL
# SELF_IP =  "192.168.1.190"  # set to static IP address of Raspberry Pi
# SELF_IP =  "192.168.1.191"  # set to static IP address of Raspberry Pi
# SELF_IP =  "192.168.1.192"  # set to static IP address of Raspberry Pi
# SELF_IP =  "192.168.1.193"  # set to static IP address of Raspberry Pi
# SELF_IP =  "192.168.1.194"  # set to static IP address of Raspberry Pi

#------------------------------------------------------
# FLASK APP
#------------------------------------------------------

FLASK_HOST = '0.0.0.0'  # leave as 0.0.0.0 to accept al incoming connections

#------------------------------------------------------
# ZMQ
#------------------------------------------------------

ZMQ_SOCKET_IP = "tcp://127.0.0.1"
ZMQ_SOCKET_PORT = "62830"

#------------------------------------------------------
# TORNADO / WEBSOCKET
#------------------------------------------------------

TORNADO_PORT = 31415    # DO NOT MODIFY!!

#------------------------------------------------------
# OPC / FADECANDY SERVER
#------------------------------------------------------

OPC_ADDR = 'localhost:7890' # MUST match fcserver.json in /usr/local/bin

#------------------------------------------------------
# QUEUE
#------------------------------------------------------

QUEUE_MAX = 3           # max number of users. This includes those waiting, and the controller; if full, user will be asked to try again later
QUEUE_MAX_TIME = 300    # time (in seconds) a user has to control LEDs before control is passed to next in queue

#------------------------------------------------------
# TIME ON/OFF
#------------------------------------------------------

TIME_ON_HOUR = 17       # hour to turn on (24 hour time) 17 = 5PM
TIME_OFF_HOUR = 23      # hour to turn off (24 hour time) 23 = 11PM

#------------------------------------------------------
# DISPLAY TYPE
#------------------------------------------------------

PI_DISPLAY_TYPE = 0     # (0) = Addressable LED strips
                        # (1) = GPIO/Relay OR DMX Lights

RELAY_LOGIC_INV = True

#------------------------------------------------------
# GPIO PINS
#------------------------------------------------------

PSU_PIN = 11

RELAY_PINS = (  11, 13, 15, 16, 18, 22, 24, 26)
#               R   G   B   W   C1  C2  C3  C4 

#------------------------------------------------------
# LED SETUP
#------------------------------------------------------

NUM_LEDS = 918          # Lower Windows LED total
NUM_LEDS = 708          # Lower Windows LED total

LED_POWER_LIMIT = True  # enable (True) power limit on LED effects that use all (or  most) pixels
LED_POWER_SCALE = 0.8   # factor to limit LED power; < 1 reduces LED brightness/power

FC_CAHNNELS = 3         # number of Fadecandy OPC channels - 1 OPC channel per window for easy addressing!

CHAN_1_NUM_LEDS = 236   # number of LEDs in channel

# idle LED effect
IDLE_COLOR_CHANGE_TIME = 20
IDLE_SYNC_OFFSET01 = 0.4
IDLE_MODE_CHANGE_TIME = 300

# window configuration
WIN_UPPER_PANE = False
WIN_PANE1 = [0,236]     #[0,50]
WIN_PANE2 = [236,472]   #[50,100]
WIN_PANE3 = [472,708]   #[100,150]
WIN_PANE4 = [708,918]   #[150,192]
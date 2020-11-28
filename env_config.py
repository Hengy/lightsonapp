
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

TIME_ON = 17        # hour to turn on (24 hour time) 17 = 5PM
TIME_OFF = 23       # hour to turn off (24 hour time) 23 = 11PM

#------------------------------------------------------
# LED SETUP
#------------------------------------------------------

NUM_LEDS = 320          # TOTAL number of LEDs in window

FC_CAHNNELS = 3         # number of Fadecandy OPC channels - 1 OPC channel per window for easy addressing!

CHAN_1_NUM_LEDS = 236   # number of LEDs in channel

#------------------------------------------------------
# FLASK APP
#------------------------------------------------------

# Matt H Dev
SELF_IP =  "192.168.0.41"  # set to static IP address of Raspberry Pi

# SPL
# SELF_IP =  "192.168.1.190"  # set to static IP address of Raspberry Pi
# SELF_IP =  "192.168.1.191"  # set to static IP address of Raspberry Pi
# SELF_IP =  "192.168.1.192"  # set to static IP address of Raspberry Pi
# SELF_IP =  "192.168.1.193"  # set to static IP address of Raspberry Pi
# SELF_IP =  "192.168.1.194"  # set to static IP address of Raspberry Pi

#------------------------------------------------------
# FLASK APP
#------------------------------------------------------

FLASK_HOST = '0.0.0.0'  # leave as 0.0.0.0 to accept 

#------------------------------------------------------
# ZMQ
#------------------------------------------------------

ZMQ_SOCKET_IP = "tcp://127.0.0.1"
ZMQ_SOCKET_PORT = "62830"

#------------------------------------------------------
# TORNADO / WEBSOCKET
#------------------------------------------------------

TORNADO_PORT = 31415

#------------------------------------------------------
# OPC / FADECANDY SERVER
#------------------------------------------------------

OPC_ADDR = 'localhost:7890'

#------------------------------------------------------
# QUEUE
#------------------------------------------------------

QUEUE_MAX = 3
QUEUE_MAX_TIME = 20

#------------------------------------------------------
# LED SETUP
#------------------------------------------------------

NUM_LEDS = 320
import tornado.ioloop
import tornado.web
import tornado.websocket

import os

import logging

import multiprocessing

import opc

import zmq
from zmq.eventloop.ioloop import ZMQIOLoop
from zmq.eventloop.zmqstream import ZMQStream

import json

import uuid

import time

import pickle

import fadecandy_ledctrl as fc
import dmxctrl as dmx

import env_config

from functools import partial

class WebSocketHandler(tornado.websocket.WebSocketHandler):
    connections = set()
    _ledp = None
    _conn = None

    # set process and pipe handles
    def initialize(self, ledp, conn):
        self._ledp = ledp
        self._conn = conn

    # accept any connection ---SECURITY!!!---
    def check_origin(self, origin):
        return True

    # on webscoket connection opened
    def open(self):
        self.connections.add(self)
        print("connection open")

    # on webscoket connection recieve message
    def on_message(self, message):
        print(message)
        process_msg(message, self._ledp, self._conn)

    # on webscoket connection closed
    def on_close(self):
        self.connections.remove(self)
        print("connection closed")

user_IP = None
user_UUID = None

# process incomoing message
def process_msg(jsonmsg, ledp, conn):
    print(jsonmsg)
    msg = json.loads(jsonmsg)
    if msg["CMD"] == "END":    # if "END", shutdown everything
        conn.send("END")
        ledp.join()
        print("Ending parent...")
        exit()
        
    else:
        print("Controller UUID: ", user_UUID)
        print("Msg UUID: ", msg["uuid"])

        if msg["uuid"] == user_UUID:
            if msg["IP"] == user_IP:
                conn.send(jsonmsg)
            else:
                print("NO IP MATCH")
        else:
            print("NO UUID MATCH")
            


def process_zmq_message(msg, conn):
    recv_msg = json.loads(msg[0])
    print(recv_msg)

    global user_UUID
    global user_IP

    if recv_msg["message"] == "New Controller":
        user_IP = recv_msg["IP"]
        user_UUID = recv_msg["uuid"]

    if recv_msg["message"] == "Stop Controller":
        user_IP = None
        user_UUID = None
        conn.send(json.dumps({"CMD":"IDLE"}))

    if recv_msg["message"] == "IDLE":
        print("IDLE", recv_msg)
        conn.send(json.dumps({"CMD":"IDLE"}))



def main():
    print("Websocket Server Process ID: ", os.getpid())

    print("Local IP Address: ", env_config.get_self_ip())
    print("Now env_config SELF_IP is: ", env_config.SELF_IP)

    env_config.config_leds()

    print("Upper Pane: ", env_config.WIN_UPPER_PANE)
    print("Display type (0 = LEDs, 1 = DMX/Relays): ", env_config.PI_DISPLAY_TYPE)

    # set up Zero MQ connection to Flask server
    flask_context = zmq.Context()
    socket = flask_context.socket(zmq.PAIR)
    print("Binding to port 62830")
    #socket.bind("tcp://127.0.0.1:62830")
    socket.bind(env_config.ZMQ_SOCKET_IP + ":" + env_config.ZMQ_SOCKET_PORT)

    # set up multiprocessing pipes
    ws_ledp_conn, ledp_conn = multiprocessing.Pipe()

    if not env_config.PI_DISPLAY_TYPE:

        # initialize fadecandy led control class
        led_controller = fc.LEDController()

    else:

        # initialize dmx light control class
        led_controller = dmx.LEDController()

    # get new process
    ledp = multiprocessing.Process(target=led_controller.run, args=[ledp_conn])

    # message callback
    flask_stream = ZMQStream(socket)
    flask_stream.on_recv(partial(process_zmq_message, conn=ws_ledp_conn), copy=True)

    ledp.start()    # start led controller process

    # create websocket listener
    websocket_listener = tornado.web.Application([
        (r"/ledctrl", WebSocketHandler, dict(ledp=ledp, conn=ws_ledp_conn))
    ])

    # # listen to websocket indefinitely
    # websocket_listener.listen(31415)
    websocket_listener.listen(env_config.TORNADO_PORT)
    tornado.ioloop.IOLoop.current().start()



if __name__ == "__main__":
    main()
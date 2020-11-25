from flask import Flask, render_template, request, session, url_for, redirect
from flask_socketio import SocketIO, emit
from flask_socketio import send as sendio

import os
import subprocess

import time

import zmq

import json

import uuid

import pickle

from apscheduler.schedulers.background import BackgroundScheduler

import env_config

# -----------------------------------------------------
# FLASK CONFIG
# -----------------------------------------------------
app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SECRET_KEY'] = b'6hc/_gsh,./;2ZZx3c6_s,1//'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
socketio = SocketIO(app,cors_allowed_origins="*")

# -----------------------------------------------------
# USER QUEUE
# -----------------------------------------------------
user_queue = []

# -----------------------------------------------------
# USER CLASS
# -----------------------------------------------------
class Controller():
  _controller = False
  _IP = None
  _position = None
  _UUID = None
  _time_start = None
  _time_end = None
  
  # -----------------------------------------------------
  # class init
  # -----------------------------------------------------
  def __init__(self, IP, pos, ctrl):
    self._controller = ctrl
    self._IP = IP
    self._position = pos
    self._UUID = uuid.uuid1()
    self._time_start = time.time()

  # returns user IP address
  def get_IP(self):
    return self._IP

  # returns user position in queue
  def get_position(self):
    return self._position

  # set user position in queue
  def set_position(self, pos):
    self._position = pos

  # decrement user position in queue
  def decr_position(self):
    self._position -= 1

  # returns if user is current LED controller
  def get_ctrl(self):
    return self._controller

  # set user LED controller status
  def set_ctrl(self, ctrl):
    self._controller = ctrl

  # return user UUID
  def get_uuid(self):
    return self._UUID

  # return time user was created (added to queue)
  def get_time_start(self):
    return self._time_start

  # return user end of session time
  def get_time_end(self):
    return self._time_end

  # set user end of session time
  def set_time_end(self, t):
    self._time_end = t


# -----------------------------------------------------
# ZMQ global context
# -----------------------------------------------------
ws_context = zmq.Context()


# -----------------------------------------------------
# Check if current controller time has elapsed
# -----------------------------------------------------
def controllercheck():

  popped = False

  if len(user_queue) > 0:
    if user_queue[0].get_time_end() <= time.time(): # if controller time had expired
      print("new controller!")

      if len(user_queue) > 1:
        print("next!")
        for i in range(1, len(user_queue)):
          user_queue[i].decr_position()
        
        user_queue[0].set_ctrl(True)
        user_queue[0].set_time_end(time.time() + env_config.QUEUE_MAX_TIME)
      
      user_queue.pop(0)
      popped = True

  return popped


def queuedcheck(uuid):
  position = None
  for i in range(len(user_queue)):
    if user_queue[i].get_ctrl():
      position = i

  return position

# -----------------------------------------------------
# Send ZMQ message to Fadecandy Web API process
# -----------------------------------------------------
def send_zmq_msg(msg, uuid, ip):
  # set up Zero MQ connection to websocket server
  socket = ws_context.socket(zmq.PAIR)
  #socket.connect("tcp://127.0.0.1:62830")
  socket.connect(env_config.ZMQ_SOCKET_IP + ":" + env_config.ZMQ_SOCKET_PORT)

  response = {"message":msg, "uuid":uuid, "IP": ip}

  socket.send_json(response)
  socket.close()


# -----------------------------------------------------
# INDEX
# -----------------------------------------------------
@app.route("/")
def index():
  
  queue_len = len(user_queue)
  if 'uuid' in session:
    # session in progress
    return render_template("index.html", queue_len=queue_len, in_progress=True)
  else:
    return render_template("index.html", queue_len=queue_len, in_progress=False)


# -----------------------------------------------------
# HTTP Polling heartbeat
# DEPRECATED - replaced by websockets
# -----------------------------------------------------
# @app.route("/heartbeat")
# def hearbeat():
  
#   queue_empty = True
#   if len(user_queue) > 0:
#     queue_empty = False

#   in_progress = False
#   if 'uuid' in session:
#     in_progress = True

#   return render_template("index.html", queue_empty=queue_empty, in_progress=in_progress)


# -----------------------------------------------------
# END
# Ends session; removes controller from queue
# -----------------------------------------------------
@app.route("/end")
def end():
  send_zmq_msg("IDLE", None, None)

  send_zmq_msg("Stop Controller", None, None)

  if not session.get('uuid') is None: # if uuid session variable exists
    session.pop('uuid', None)

  if len(user_queue) > 0:
    user_queue.pop(0)
    if len(user_queue) > 0:
      user_queue[0].set_ctrl(True)

      for i in range(len(user_queue)):
        user_queue[i].decr_position()

  return redirect(url_for('.index'), code=307)


# -----------------------------------------------------
# ADD TO QUEUE
# Adds new user to queue
# -----------------------------------------------------
@app.route("/addtoqueue")
def addtoqueue():
  
  user = None
  if len(user_queue) == 0:
    # empty queue, give control right away

    print("Adding user. First in queue.")

    user = Controller(request.remote_addr, len(user_queue), True)
    user.set_time_end(time.time() + env_config.QUEUE_MAX_TIME)
    user_queue.append(user)

    session['uuid'] = user.get_uuid()

    send_zmq_msg("New Controller", str(user.get_uuid()), str(request.remote_addr))

    return redirect(url_for('ledctrl'), code=307)

  elif len(user_queue) < env_config.QUEUE_MAX:
    # queue not empty, add to queue

    print("Adding user to queue. Position ", len(user_queue) + 1)

    user = Controller(request.remote_addr, len(user_queue), False)
    user.set_time_end(time.time() + (len(user_queue) * env_config.QUEUE_MAX_TIME))
    user_queue.append(user)

    session['uuid'] = user.get_uuid()

    return render_template("queuewait.html", queue_full=False)
  
  else:
    # queue is full

    print("Queue full!")

    return render_template("queuefull.html", queue_full=True)


# -----------------------------------------------------
# LED CONTROL
# Allows controller to control LEDs
# -----------------------------------------------------
@app.route("/ledctrl")
def ledctrl():

  if not session.get('uuid') is None: # if uuid session variable exists
    if user_queue[0].get_uuid() == session.get('uuid'):
    
      return render_template("ledctrl.html", data={"uuid":session.get('uuid'), "ip":str(request.remote_addr)})

    else:

      print("ERROR! Should not be able to control LEDs at this time")

      return redirect(url_for('addtoqueue'), code=307)
    
  else:

    print("ERROR!")

    return redirect(url_for('.index'), code=307)


# -----------------------------------------------------
# Gives all templates the SELF_IP variable
# -----------------------------------------------------
@app.context_processor
def inject_selfip():
    return dict(self_ip=env_config.SELF_IP)


# -----------------------------------------------------
# ON SCIKETIO CONNECT
# -----------------------------------------------------
@socketio.on('connect')
def test_connect():
  print("Client SocketIO connected")

# -----------------------------------------------------
# ON SCIKETIO 'SWITCH CONTROL' EVENT
# -----------------------------------------------------
@socketio.on('switch control')
def switchctrl_handler(json, methods=['POST']):
  print('Recieved JSON: ' + str(json))

# -----------------------------------------------------
# ON SCIKETIO 'CHECK' EVENT
# Replaces HTTP heartbeat; checks if controller end time
# has been reached - returns True if time has elapsed
# -----------------------------------------------------
@socketio.on('check')
def check_handler(jsonmsg, methods=['POST']):
  time_expired = controllercheck()
  if time_expired:
    print("Check handled; time expired")
  data = json.dumps({"check_result":time_expired})
  emit('check_result', data)


# -----------------------------------------------------
# LIGHTS ON FLASK APP MAIN
# -----------------------------------------------------
if __name__ == "__main__":

  print("Flask Process ID: ", os.getpid())

  # app.run(host='0.0.0.0',debug=True)
  socketio.run(app,host=env_config.FLASK_HOST,debug=True)

# if __name__ == "__main__":
#   main(None)

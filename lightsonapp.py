from flask import Flask, render_template, request, session, url_for, redirect
from flask_socketio import SocketIO, emit

import os
import subprocess

import time

import zmq

import json

import uuid

import pickle

from apscheduler.schedulers.background import BackgroundScheduler

# flask
app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SECRET_KEY'] = b'6hc/_gsh,./;2ZZx3c6_s,1//'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
socketio = SocketIO(app,cors_allowed_origins="*")

# queue
user_queue = []

# current user
class Controller():
  _controller = False
  _IP = None
  _position = None
  _UUID = None
  _time_start = None
  _time_end = None
  
  def __init__(self, IP, pos, ctrl):
    self._controller = ctrl
    self._IP = IP
    self._position = pos
    self._UUID = uuid.uuid1()
    self._time_start = time.time()

  def get_IP(self):
    return self._IP

  def get_position(self):
    return self._position

  def set_position(self, pos):
    self._position = pos

  def decr_position(self):
    self._position -= 1

  def get_ctrl(self):
    return self._controller

  def set_ctrl(self, ctrl):
    self._controller = ctrl

  def get_uuid(self):
    return self._UUID

  def get_time_start(self):
    return self._time_start

  def get_time_end(self):
    return self._time_end

  def set_time_end(self, t):
    self._time_end = t

ws_context = zmq.Context()


def queuecheck():
  print("checking user queue")

def send_zmq_msg(msg, uuid, ip):
  # set up Zero MQ connection to websocket server
  socket = ws_context.socket(zmq.PAIR)
  socket.connect("tcp://127.0.0.1:62830")

  response = {"message":msg, "uuid":uuid, "IP": ip}

  socket.send_json(response)
  socket.close()

@app.route("/")
def index():
  
  queue_len = len(user_queue)
  if 'uuid' in session:
    # session in progress
    return render_template("index.html", queue_len=queue_len, in_progress=True)
  else:
    return render_template("index.html", queue_len=queue_len, in_progress=False)

@app.route("/heartbeat")
def hearbeat():
  
  queue_empty = True
  if len(user_queue) > 0:
    queue_empty = False

  in_progress = False
  if 'uuid' in session:
    in_progress = True

  return render_template("index.html", queue_empty=queue_empty, in_progress=in_progress)

@app.route("/end")
def end():
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

@app.route("/addtoqueue")
def addtoqueue():
  
  user = None
  if len(user_queue) == 0:
    # empty queue, give control right away

    print("Adding user. First in queue.")

    user = Controller(request.remote_addr, len(user_queue), True)
    user_queue.append(user)

    session['uuid'] = user.get_uuid()

    send_zmq_msg("New Controller", str(user.get_uuid()), str(request.remote_addr))

    return redirect(url_for('ledctrl'), code=307)

  elif len(user_queue) < 3:
    # queue not empty, add to queue

    print("Adding user to queue.")

    user = Controller(request.remote_addr, len(user_queue), False)
    user_queue.append(user)

    session['uuid'] = user.get_uuid()

    return render_template("queue.html", queue_full=False)
  
  else:

    print("Queue full!")

    return render_template("queue.html", queue_full=True)



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


@socketio.on('connect')
def test_connect():
  print("Client SocketIO connected")
  emit('after connect',  {'data':'Lets dance'})

@socketio.on('switch control')
def handle_my_custom_event(json, methods=['POST']):
    print('Recieved JSON: ' + str(json))


if __name__ == "__main__":

  print("Flask Process ID: ", os.getpid())

  scheduler = BackgroundScheduler()
  scheduler.add_job(queuecheck, 'interval', seconds=2)
  scheduler.start()

  # app.run(host='0.0.0.0',debug=True)
  socketio.run(app,host='0.0.0.0',debug=True)

# if __name__ == "__main__":
#   main(None)

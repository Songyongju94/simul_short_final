import sys
import json
from flask import Flask
from flask import request
from SignalDetectorApp import SignalDetectorApp
from Definition import Definition
from kowanasutil import Log
app = Flask(__name__)
definition = Definition()
sys.stdout.flush()

def __handle(processApp, name, request):
    if request.method == 'GET':
        return processApp.handle(name, request.args).toJson()
    elif request.method == 'POST':
        return processApp.handlePost(name, json.loads(request.data)).toJson()

@app.route("/trdetected", methods = ['GET'])
def trdetected():

    signalDetectorApp = SignalDetectorApp(definition.getDb())
    return __handle(signalDetectorApp, 'trdetected', request)

@app.route("/registerdevice", methods = ['POST'])
def registerdevice():
    signalDetectorApp = SignalDetectorApp(definition.getDb())
    return __handle(signalDetectorApp, 'registerdevice', request)

@app.route("/settings", methods = ['GET', 'POST'])
def settings():
    signalDetectorApp = SignalDetectorApp(definition.getDb())
    return __handle(signalDetectorApp, 'settings', request)

if __name__ == "__main__":
    app.run(host='0.0.0.0')
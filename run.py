import sys
from kowanasutil import Log
from SignalDetectorService import SignalDetectorService

class Runner:
    __services = {}
    def __init__(self, service, logfile):
        self.__log = Log(logfile = logfile)
        self.__createService(service)
    
    def __createService(self, name):
        if name == 'signaldetector':
            self.__services['signaldetector'] = SignalDetectorService('Signal Detector Service')
            self.__services['signaldetector'].run()

if __name__ == '__main__':
    if len(sys.argv) > 2: 
        service = sys.argv[1]
        logfile = sys.argv[2]
        runner = Runner(service, logfile)

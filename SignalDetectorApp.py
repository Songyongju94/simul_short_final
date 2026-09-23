import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from kowanasutil import DBConnection, ApiHandler, Config
from model import DeviceRepository, SettingRepository
from Definition import Definition
import json

class SignalDetectorApp(ApiHandler):
    __dbname = None
    __dbConnection = None
    __dbConnection5min = None

    def __init__(self, dbname):
        self.__definition = Definition()
        self.__config = Config(file=self.__definition.getConfig2())
        self.__dbname = dbname

    def connectDB(self):
        self.__dbConnection = DBConnection(self.__dbname, self.__config)
        self.__dbConnection.connect()
        return self.__dbConnection

    def disconnectDB(self):
        self.__dbConnection.disconnect()

    def _handleCreate(self, api, args):
        if api == 'registerdevice':
            self.connectDB()
            devices = DeviceRepository(self.__dbConnection)
            result = devices._handleCreate(api, args)
            self.disconnectDB()
            return result
        elif api == 'settings':
            self.connectDB()
            settings = SettingRepository(self.__dbConnection)
            result = settings._handleCreate(api, args)
            self.disconnectDB()
            return result

    def _handleRead(self, api, args):
        if api == 'trdetected':
            self.connectDB()
            self.disconnectDB()
            return result
        elif api == 'settings':
            self.connectDB()
            settings = SettingRepository(self.__dbConnection)
            result = settings._handleRead(api, args)
            self.disconnectDB()
            return result
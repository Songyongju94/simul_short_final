import time
from kowanasutil import DBConnection, DBModel, ApiHandler, DBField, DBFieldUID, ApiResult

class DeviceRepository(DBModel, ApiHandler):
    def __init__(self, dbConnection):
        fields = [DBFieldUID(DBModel.Int, 36, DBField.AutoIncrement),
                  DBField('token', DBModel.String, 1024)]
        super().__init__(dbConnection, 'device', fields=fields, debug=False)

    def __isExist(self, devices, token):
        for device in devices:
            if device[1] == token:
                return True
        return False

    def _handleCreate(self, api, args):
        devices = self.readAll()
        if not self.__isExist(devices, args['token']):
            self.add([DBModel.AUTO_INCREMENT, args['token']])
            self.commit()
        return self._createResult(success=True)

    def readTokens(self):
        values = self.readAll()
        return [value[1] for value in values]
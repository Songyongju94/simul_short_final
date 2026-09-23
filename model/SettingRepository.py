import time
from kowanasutil import DBConnection, DBModel, ApiHandler, DBField, DBFieldUID, ApiResult, KowanasTime, Log
class SettingRepository(DBModel, ApiHandler):
    def __init__(self, dbConnection):
        fields = [DBFieldUID(DBModel.String, 36),
                  DBField('value', DBModel.String, 128)]
        super().__init__(dbConnection, 'setting', fields=fields, debug=False)
        self.__settings = self.readAllToDict()
        self.__log = Log()

    def _handleRead(self, api, args):
        result = [{key: value[1]} for key, value in self.__settings.items()]
        return self._createResult(success=True, data=result)

    def _handleCreate(self, api, args):
        if args['key'] == 'noti':
            if 'noti' not in list(self.__settings.keys()): 
                self.add(['noti', [args['value']]])
            else:
                self.update('noti', ['noti', args['value']])
            self.commit()
        return self._createResult(success=True)

    def setHedgeMode(self, isHedge, position, count, quantity):
        now = KowanasTime.getKST()
        dateTime = now.strftime('%Y-%m-%d %H:%M')
        self.__log.d('setHedgeMode hedge=', isHedge, ' quantity=', quantity, ' ', dateTime)
        try:
            if 'hedge' not in list(self.__settings.keys()):
                self.add(['hedge', isHedge])
                self.add(['position', position])
                self.add(['count', str(count)])
                self.add(['quantity', str(quantity)])
                self.add(['dateTime', dateTime])
            else:
                self.update('hedge', ['hedge', isHedge])
                self.update('position', ['position', position])
                self.update('count', ['count', str(count)])
                self.update('quantity', ['quantity', str(quantity)])
                self.update('dateTime', ['dateTime', dateTime])
            self.commit()
            self.__log.d('set hedge mode successfully hedge=', isHedge, ' count=', count, 'position=', position)
        except Exception as e:
            self.__log.d(e)

        if isHedge == 'True':
            return [True, position, count, quantity]
        else:
            return [False, position, count, quantity]

    def getHedgeMode(self):
        values = self.readAllToDict()
        if len(values) == 0:
            return [False, None, None, None]
        value = values['hedge'][1]
        if value == 'False':
            return [False, None, None, None]
        elif value == 'True':
            return [True, values['position'][1], int(values['count'][1]), float(values['quantity'][1])]
        else:
            return [False, None, None, None]

    def getNoti(self):
        values = self.readAllToDict()
        value = values['noti'][1]
        if value == 'False':
            return False
        elif value == 'True':
            return True

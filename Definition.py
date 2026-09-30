class Definition:
    def __init__(self):
        self.isServer = False

    def getConfig1(self):
        if self.isServer:
            return '/home/ubuntu/workspace/signaldetector_server17/.config'
        else:
            return '../.config'

    def getConfig2(self):
        if self.isServer:
            return '/home/ubuntu/workspace/signaldetector_server17/.config'
        else:
            return '.config'

    def getDb(self):
        return 'db_sd17'

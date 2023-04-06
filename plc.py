import snap7
from snap7.types import Areas,WordLen
from mtypes import Data_db

# read plc
class ysnap:
    def __init__(self):
        super().__init__()
        self.ip='127.0.0.1'
        self.slot=3
        self.connected=False
        self.g=[]  # test good
        self.ng=[]  # test not good
        
    def isConnected(self):
        if self.client.get_connected():
            self.connected=True
            print('connected')
        else:
            self.connected=False
            print('not connected')
    
    def connect(self):        
        self.client=snap7.client.Client()
        try:
            self.isConnected()
            if not self.connected:
                self.client.connect(self.ip, 0, self.slot)
            self.isConnected()
        except Exception as e:
            print('connect failure:%s' % e)
    def disconnect(self):
        self.client.disconnect()

    def read(self):
        
        pass
    def get_clent(self):
        return self.client
        

# 线程
import threading

class thread(threading.Thread):
    def __init__(self,client,t_name,t_id,data):
        threading.Thread.__init__(self)
        self.client=client
        self.t_name=t_name
        self.t_id=t_id
        self.data=data
    def run(self):
        print('thread run...')
        print('areas:',self.data.areas)
        print(self.data.areas,self.data.number,self.data.start,self.data.size)
        rs=self.client.read_area(self.data.areas,self.data.number,self.data.start,self.data.size)
        print('time cost:%d' % self.client.get_exec_time())
        rs2=self.client.db_get(3220)
        print('time cost:%d' % self.client.get_exec_time())
        print(rs)


if __name__=='__main__':
    
    y=ysnap()
    y.connect()
    client=y.get_clent()

    db=Data_db('u1','db128.dbx0.7',Areas.DB,128,0,10,1)
    thread1=thread(client,'a',1,db)
    thread1.start()

    print('finished')

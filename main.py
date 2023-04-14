from PySide2.QtCore import (
    QFile,
    QIODevice,
    QObject,
    QRunnable,
    QThread,
    QThreadPool,
    QTimer,
    Qt,
    Slot,
    Signal,
    QMutex,
    QMimeData,
    QModelIndex,
)
from PySide2.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QTreeWidget,
    QMessageBox,
    QMenu, 
    QTreeView, 
    QAction, 
    QPushButton, 
    QLineEdit, 
    QTableWidget, 
    QHeaderView,
    QListWidgetItem,
)
from PySide2.QtGui import QDrag,QStandardItemModel
from PySide2 import QtGui
from functools import partial
from snap7.types import Areas,WordLen
from yio import Io
from curve import Curve
from db import Db
from ymenu import Menu
from struct import unpack
from datetime import datetime
from queue import Queue

import sys
import random
import snap7
import yaml
import time
import util 
import threading
import concurrent.futures
import pyqtgraph as pg


uiclass, baseclass = pg.Qt.loadUiType("main.ui")
mutex=QMutex()
MaxThreadCount=5 #线程池尺寸


# 线程函数
class MyWorker(QRunnable):
    def __init__(self,name, queue,delay):
        super().__init__()
        self.name=name
        self.queue=queue
        self.delay=delay
        self.running=True

    def run(self):
        while True:
            if not self.running:
                return
                
            if not self.queue.empty():
                q=self.queue.get() #取1个值
                if q is not None and q.enable: # 激活
                    q.read()
                self.queue.put(q)
                #print('running:%s, %s' % (self.name,q.db_data.address))
            
            QThread.msleep(self.delay*10)
    
    # 设置运行标志
    def set_stop(self):
        self.running=False

# 变量类画图
class VcPlot(QObject):
    def __init__(self,name,address,widget):
        #self.vid=vid
        self.name=name
        self.address=address
        self.widget=widget
        self.plot=None
        self.pen = pg.mkPen(color=self.random_color(), width=1, style=Qt.SolidLine)
        self.x=[]
        self.y=[]
        
        self.mplot()
    
    @Slot(list) #x,y,addr
    def move(self,data_list):
        if self.address==data_list[2]: #地址相符的更新
            self.x.append(data_list[0])
            self.y.append(data_list[1])
            if len(self.x)>1000:
                self.x=self.x[1:]
                self.y=self.y[1:]
            
    def mplot(self):
        self.plot=self.widget.plot(self.x,self.y,pen=self.pen,symbol='+',symbolSize=3,symbolBrush=('b'))
    
    @Slot(str)
    def update_plot(self,msg):
        self.plot.setData(self.x,self.y)
    
    def get_plot(self):
        return (self.vid,self.plot)
    
    #随机颜色
    def random_color(self): 
        '''
        随机颜色r g b
        '''       
        r = random.randint(0,255)
        g = random.randint(0,255)
        b = random.randint(0,255)
        return (r,g,b)

# 变量类 variable class
class Vc(QObject):
    data_readed=Signal(list)
    
    def __init__(self,client,db,db_data):
        super().__init__()
        self.name=db_data.name
        self.client=client
        self.db=db
        self.db_data=db_data
        self.xv=[]
        self.yv=[]
        self.enable=False
        
        self.data_type={
        'bool':'B',
        'word':'>h',
        'int':'>i',
        'real':'>f'
        }
        
    # 响应 data_update 
    @Slot(str)
    def hi(self, m_str):
        print('hi, %s-%s'%(self.name, m_str))
        
    def read_data(self):
        #读数据
        #使用mutex保护client
        mutex.lock() #锁上
        data_b=None
        try:
            data_b=self.client.read_area(
                self.db_data.areas,
                self.db_data.number,
                self.db_data.start,
                self.db_data.size
            )
        except AttributeError:
            print('line 119 at main, client is None')
            return -1,-1
        mutex.unlock() #开锁
        #example
        #rs=self.client.read_area(Areas.DB,128,0,1)
        data_str='-1'
        data_raw=''
        data_value=0
        data_value_str=''
        try:
            data_str=unpack(self.data_type[self.db_data.data_type], data_b)
            if len(data_b)==1:
                data_b=b'\x00'+data_b
            data_raw=data_b.decode(encoding='utf_16_be')
            data_value,data_value_str=self.cal_v(data_b,self.db_data)
        except Exception as e:
            print('Line 131 in main.py: ',str(e),self.db_data.address,data_b)
        #print('%s: %s, cost %d.' % (self.db_data.address,data_b,self.client.get_exec_time()))
        #print(self.db_data.address,self.db_data.areas,self.db_data.number,self.db_data.start,self.db_data.size,data_b,data_value)
        
        #写入数据库
        self.db.save(
            self.db_data.device,
            self.db_data.name,
            self.db_data.address,
            self.db_data.bit_pos,
            data_raw,
            data_value_str,
            self.db_data.data_type
        )
        # 返回x, y
        return datetime.now().timestamp(), data_value  
        
    def read(self):
        x,y=self.read_data()
        #发射信号
        self.data_readed.emit([x,y,self.db_data.address])
        
    # bytearray计算值
    # q: bytearray, t: data type
    def cal_v(self,q,db_data): 
        xv=0
        #bool
        if db_data.data_type=='bool':  
            #utf_16_be 将1字节编码为2字节
            xv=1 if snap7.util.get_bool(q,1,db_data.bit_pos) else 0
        #word
        if db_data.data_type=='word':
            xv=snap7.util.get_int(q,0)
        #int
        if db_data.data_type=='int':
            xv=snap7.util.get_dint(q,0)
        #real
        if db_data.data_type=='real':
            xv=snap7.util.get_real(q,0)
        #print(db_data.data_type,xv)
        return xv,str(xv)
    
    #启用/禁用    
    def set_enable(self, flag):
        self.enable=flag
    
    def get_enable(self):
        return self.enable

class MyPlotWidget(pg.PlotWidget):
    '''
    拖曳事件
    '''
    #拖曳信号
    item_droped=Signal(dict)

    def init(self, parent=None):
        super().init(parent)

        self.widget_min_height=160
        self.plotItem.setBackground('w') 
        self.showGrid(x=True,y=True)
        self.addLegend()
        self.plotItem.setAxisItems({'bottom': pg.DateAxisItem()})
        self.setMinimumHeight(self.widget_min_height) 

    def dragMoveEvent(self, event):
        src=event.source()
        if src and src!=self:
            event.setDropAction(Qt.MoveAction)

    def dragEnterEvent(self, event):
        #改指示
        if event.mimeData().hasFormat('application/x-qstandarditemmodeldatalist'):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        data = event.mimeData()
        source_item = QStandardItemModel()
        source_item.dropMimeData(data, Qt.CopyAction,0,0,QModelIndex())
        name=source_item.item(0, 0).text()
        print('Droped:', name)
        self.item_droped.emit({'name':name,'widget':self,'msg':'drop'})

# 主函数
class Main(uiclass, baseclass):
    plot_update=Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        # action Io       
        self.io = Io()
        self.action_io.triggered.connect(self.io.show)
        self.dbs=self.io.list_var
        self.client=self.io.client
        # action Curve
        self.curve=Curve()
        self.action_his.triggered.connect(self.curve.show)

        # 线程池
        self.pool=QThreadPool.globalInstance()        
        self.pool.setMaxThreadCount(MaxThreadCount) # 线程池尺寸 

        # 定时刷新图形
        self.timer=QTimer()
        self.timer.setInterval(1000) #1s
        self.timer.timeout.connect(partial(self.plot_update.emit,'hi'))
        
        # 数据
        self.db=Db()
        
        self.menu=Menu(self.tree)

        self.menu_items=[] #树形菜单项集
        self.menu.item_changed.connect(self.menu_dblclick)
        #连接双击信号
        self.menu.item_dblclicked.connect(self.menu_dblclick2)
        
        self.fields=[]
        
        # 线程
        # 对应不同时间的队列
        self.queue_10ms=Queue()
        self.queue_20ms=Queue()
        self.queue_50ms=Queue()
        self.queue_100ms=Queue()
        self.queue_1s=Queue()
        self.queues={
            '10ms':self.queue_10ms,
            '20ms':self.queue_20ms,
            '50ms':self.queue_50ms,
            '100ms':self.queue_100ms,
            '1s':self.queue_1s,
        }
        self.queue_vc=[] #读数队列
        self.queue_plot=[] #绘图队列
        
        # 实例化
        self.worker_10ms=MyWorker('10ms',self.queue_10ms,10)
        self.worker_20ms=MyWorker('20ms',self.queue_20ms,20)
        self.worker_50ms=MyWorker('50ms',self.queue_50ms,50)
        self.worker_100ms=MyWorker('100ms',self.queue_100ms,100)
        self.worker_1s=MyWorker('1s',self.queue_1s,1000)
        # 启动
        self.pool.start(self.worker_10ms)
        self.pool.start(self.worker_20ms)
        self.pool.start(self.worker_50ms)
        self.pool.start(self.worker_100ms)
        self.pool.start(self.worker_1s)

        # 变量列表
        self.vcs=[]
        for db_data in self.dbs:
            vc=Vc(self.client,self.db,db_data)
            self.vcs.append(vc)

    #end of init

    def start(self):
        '''
        启动定时器
        '''
        self.timer.start()
    
    def closeEvent(self, event):
        '''
        #重写关闭事件
        '''
        self.stop()
        print("main window is closed.")
        event.accept()        
                
    def stop(self):
        '''
        停止定时器及线程
        '''
        self.timer.stop()          
        
        self.worker_10ms.set_stop()
        self.worker_20ms.set_stop()
        self.worker_50ms.set_stop()
        self.worker_100ms.set_stop()
        self.worker_1s.set_stop() 
        self.pool.waitForDone(100)
        

        #for vc in self.vcs:
        #    vc.data_readed.disconnect()
    
    # 1次读取多个变量
    def batch_read(self):
        '''
        class S7DataItem(ctypes.Structure):
            _pack_ = 1
            _fields_ = [
                ('Area', ctypes.c_int32),
                ('WordLen', ctypes.c_int32),
                ('Result', ctypes.c_int32),
                ('DBNumber', ctypes.c_int32),
                ('Start', ctypes.c_int32),
                ('Amount', ctypes.c_int32),
                ('pData', ctypes.POINTER(ctypes.c_uint8))
            ]       
        read_multi_vars(self, items) -> Tuple[int, S7DataItem]
        Reads different kind of variables from a PLC simultaneously.
        Args:
            items: list of items to be read.
        Returns:
            Tuple with the return code from the snap7 library and the list of items.        
        '''
        pass    
    
    @Slot(list)
    def menu_dblclick(self, items):
        '''
        树形菜单项目双击
        '''
        print('main2:',items)
        self.fields=self.menu.get_menu_items()
        #修改变量类的状态
        for v in self.vcs:
            if v.name in self.fields:
                v.set_enable(True)
            else:
                v.set_enable(False)   
    
    @Slot(str)
    def menu_dblclick2(self, item):
        '''
        树形菜单双击
        '''
        #新建plotwidget
        #self.my_plot([item,None,'item double click'])
        self.my_plot({'name':item,'widget':None,'msg':'menu double click'})
        
    @Slot(dict)
    def my_plot(self, param):
        '''
        param: 0-name, 1-widget
        双击菜单项，新增组件绘图；拖曳菜单项，在组件上增加绘图
        '''

        name=param['name']
        widget=param['widget']
        print(param['msg'])

        if widget is None:
            widget=MyPlotWidget() 
            #新建实例，连接放下信号
            widget.item_droped.connect(self.my_plot)                 

        for vc in self.vcs:
            if vc.name==name:
                vc.enable=True                
                
                #布尔y设置0-1，其他格数设置为1
                if vc.db_data.data_type=='bool':
                    widget.setYRange(0,1,padding=0)                    
                
                widget.setTitle(vc.db_data.address)                                
                self.layout.addWidget(widget)
                
                #实例化
                vc_plot=VcPlot(vc.name,vc.db_data.address,widget)               
                #信号连接
                #更新
                self.plot_update.connect(vc_plot.update_plot)
                #读数
                vc.data_readed.connect(vc_plot.move)
                #绘画队列
                self.queue_plot.append(vc_plot)
                #数据读取队列               
                if vc.name not in self.queue_vc: 
                    self.queues[vc.db_data.delay].put(vc)
                    self.queue_vc.append(vc.name)
                else:
                    print('vc is already in read queue, skip.')

                #退出循环
                break

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 主窗体
    main = Main()
    main.show()
    main.start()

    sys.exit(app.exec_())

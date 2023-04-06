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
)

from PySide2 import QtGui
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
            if not self.queue.empty():
                q=self.queue.get() #取1个值
                if q.enable: # 激活
                    q.slide()
                self.queue.put(q)
                #print('running:%s, %s' % (self.name,q.db_data.address))
            # 退出
            if not self.running:
                break
            QThread.msleep(self.delay*10)
    
    # 设置运行标志
    def set_stop(self):
        self.running=False

# 变量类
class Vc(QObject):
    
    def __init__(self,client,db,db_data):
        super().__init__()
        self.name=db_data.name
        self.client=client
        self.db=db
        self.db_data=db_data
        self.xv=[]
        self.yv=[]
        self.enable=False
        self.pen = pg.mkPen(color=self.random_color(), width=1, style=Qt.SolidLine)
        self.data_type={
        'bool':'B',
        'word':'>h',
        'int':'>i',
        'real':'>f'
        }
        
        self.widget=None
        self.plot=None
        self.plot_item=None
        
        self.min_value=0
        self.max_value=99999
        
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
        #print(self.db_data.name,self.db_data.address,data_b,data_value)
        
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
        
    #滑动读数    
    def slide(self):
        if self.enable:
            x,y=self.read_data()
            self.xv.append(x)
            self.yv.append(y)
            if len(self.xv)>1000:
                self.xv=self.xv[1:]
                self.yv=self.yv[1:]            
        
    def mplot(self):
        self.plot=self.widget.plot(self.xv,self.yv,pen=self.pen,symbol='+',symbolSize=3,symbolBrush=('b'))
        
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

    #随机颜色
    def random_color(self):        
        r = random.randint(0,255)
        g = random.randint(0,255)
        b = random.randint(0,255)
        return (r,g,b)
        

# 主函数
class Main(uiclass, baseclass):
    data_update=Signal(str)
    
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
        self.timer.timeout.connect(self.refresh_plot)
        
        # 数据
        self.db=Db()
        
        self.menu=Menu(self.tree)
        self.tree.setDragDropMode(QTreeView.InternalMove)

        self.menu_items=[] #树形菜单项集
        self.menu.item_changed.connect(self.menu_dblclick)
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
        self.queue_vc=[]
        
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
            self.data_update.connect(vc.hi)
            self.vcs.append(vc)
        
    def start(self):
        self.timer.start()

    #重写关闭事件
    def closeEvent(self, event):
        self.stop()
        print("main window is closed.")
        event.accept()
        
    # 刷新绘图
    def refresh_plot(self):
        self.data_update.emit('hii')
        for v in self.vcs:
            if v.plot is not None:
                v.plot.setData(v.xv,v.yv)
        
    # 停止定时器及线程            
    def stop(self):
        self.timer.stop()  
        
        self.pool.clear()
        self.worker_10ms.set_stop()
        self.worker_20ms.set_stop()
        self.worker_50ms.set_stop()
        self.worker_100ms.set_stop()
        self.worker_1s.set_stop()          
    
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
    
    # 菜单点击
    @Slot(list)
    def menu_dblclick(self, items):
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
        #新建plotwidget
        widget=pg.PlotWidget()
        widget.setBackground('w') 
        widget.showGrid(x=True,y=True)
        widget.addLegend()
        widget.setAxisItems({'bottom': pg.DateAxisItem()})
        
        for v in self.vcs:
            if v.name==item:
                v.enable=True
                # 布尔Y设置0-1，其他格数设置为1
                if v.db_data.data_type=='bool':
                    widget.setYRange(0,1,padding=0)
                    
                v.widget=widget                
                if v.name not in self.queue_vc:
                    widget.setTitle(v.db_data.address)
                    self.plot_layout.addWidget(widget)
                    self.queues[v.db_data.delay].put(v)
                    self.queue_vc.append(v.name)
                else:
                    print('vc is already in queue, skip.')
                v.mplot()
                break
    #拖放
    def mousePressEvent(self, event):
        print(event.pos())
        if (event.button() == Qt.LeftButton and self.tree.geometry().contains(event.pos())):

            drag = QDrag(self)
            mimeData = QMimeData()
            mimeData.setText(commentEdit.toPlainText())
            drag.setMimeData(mimeData)
            dropAction=Qt.DropAction()
            drag.setPixmap(iconPixmap)
            dropAction = drag.exec()
        
     
if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 主窗体
    main = Main()
    main.show()
    main.start()

    sys.exit(app.exec_())

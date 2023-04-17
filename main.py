from PySide2.QtCore import (
    QRunnable,
    QThread,
    QThreadPool,
    QTimer,
    Slot,
    Signal,
    )

from PySide2.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,    
    )
from yio import Io
from curve import Curve
from db import Db
from ymenu import Menu
from queue import Queue
from functools import partial

from vc import MyPlotWidget,VcPlot,Vc

import pyqtgraph as pg
import sys


uiclass, baseclass = pg.Qt.loadUiType("main.ui")
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
            
            QThread.msleep(self.delay)
    
    # 设置运行标志
    def set_stop(self):
        self.running=False



# 主函数
class Main(uiclass, baseclass):
    plot_update=Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        #pg.setConfigOption('leftButtonPan',False)
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

        pg.setConfigOption('useOpenGL',True)

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
            #新建widget要放到layout上
            self.layout.addWidget(widget)
            #新建实例，连接放下信号
            widget.item_droped.connect(self.my_plot)                 

        for vc in self.vcs:
            if vc.name==name:
                vc.enable=True                
                
                #布尔y设置0-1，其他格数设置为1
                if vc.db_data.data_type=='bool':
                    widget.setYRange(0,1,padding=0)                    
                #标题：名称+地址
                title=widget.windowTitle()
                widget.setTitle('%s %s:%s'%(title,vc.db_data.name,vc.db_data.address))
                
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

from PySide2.QtCore import (
    QRunnable,
    QThread,
    QThreadPool,
    QTimer,
    Slot,
    Signal,
    QObject,
    )

from PySide2.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,   
    QWidget,
    QVBoxLayout,
    QLayout,
    )
from PySide2.QtUiTools import loadUiType

from yio import Io
from curve import Curve
from db import Db
from ymenu import Menu
from queue import Queue
from functools import partial

from matplotlib.backends.backend_qtagg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure

from vc import MyWidget,MyCanvas,VcPlot,Vc

import sys
import datetime
import time
import util

ui_class, base_class = loadUiType("main.ui")
MaxThreadCount=5 #线程池尺寸

# 线程函数
class MyWorker(QRunnable):
    def __init__(self,name, queue,delay):
        super().__init__()
        self.name=name
        self.queue=queue
        self.delay=delay
        self.running=True
        self.pause=False

    def run(self):
        while self.running:
            if self.pause:
                continue
                
            if not self.queue.empty():
                q=self.queue.get() #取1个值
                if q is not None: # 激活
                    q.read()
                #若变量失活则不放入队列循环
                if q.enable:
                    self.queue.put(q)
                #print('running:%s, %s' % (self.name,q.db_data.address))
            
            #QThread.msleep(self.delay)
            time.sleep(self.delay/1000)
    
    # 设置运行标志
    def set_running(self, flag):
        self.running=flag
    # 设置停止标志
    def set_pause(self,flag):
        self.pause=flag


# 主函数
class Main(ui_class, base_class):
    sig_plot_update=Signal(str) #信号：更新图形
    sig_app_exited=Signal(bool) #信号：程序退出   
    sig_log_record=Signal(str,str) #信号：日志
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('PLC recorder')
        # 动作
        # action: Io variable      
        self.io = Io()
        self.io.sig_log_record.connect(self.log)

        self.action_io.triggered.connect(self.io.show)
        self.dbs=self.io.list_var
        self.client=self.io.client
        # action: history curve
        self.curve=Curve()
        self.action_his.triggered.connect(self.curve.show)
        # action: start
        self.action_start.triggered.connect(self.start)
        # action: stop
        self.action_stop.triggered.connect(self.stop)

        #时间范围
        self.time_range.addItem('5s')
        self.time_range.addItem('10s')
        self.time_range.addItem('30s')
        self.time_range.addItem('60s')
        self.time_range.addItem('5min')
        self.time_range.addItem('10min')
        self.time_range.addItem('30min')
        self.time_range.setItemText (0, '5s')


        # 线程池
        self.pool=QThreadPool.globalInstance()        
        self.pool.setMaxThreadCount(MaxThreadCount) # 线程池尺寸 

        # 定时刷新图形
        self.timer=QTimer()
        self.timer.setInterval(1000) #1s
        #self.timer.timeout.connect(partial(self.sig_plot_update.emit,'hi'))
        
        # 数据
        self.db=Db()
        
        self.menu=Menu(self.tree)

        self.menu_items=[] #树形菜单项集
        self.menu.item_changed.connect(self.menu_click)
        #连接双击信号
        self.menu.item_dblclicked.connect(self.menu_dblclick)
        
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

        # 实例化线程
        self.worker_10ms=MyWorker('10ms',self.queue_10ms,10)
        self.worker_20ms=MyWorker('20ms',self.queue_20ms,20)
        self.worker_50ms=MyWorker('50ms',self.queue_50ms,50)
        self.worker_100ms=MyWorker('100ms',self.queue_100ms,100)
        self.worker_1s=MyWorker('1s',self.queue_1s,1000)

        # 启动线程
        self.pool.start(self.worker_10ms,10)
        self.pool.start(self.worker_20ms,20)
        self.pool.start(self.worker_50ms,30)
        self.pool.start(self.worker_100ms,100)
        self.pool.start(self.worker_1s,100)

        # 变量列表
        self.vcs=[]
        for db_data in self.dbs:
            vc=Vc(self.client,self.db,db_data)
            #连接log信号
            vc.sig_log_record.connect(self.log)
            self.vcs.append(vc)

    #end of init

    def start(self):
        '''
        启动线程操作
        '''  
        self.timer.start() 
        # 启动更新画面的定时器
        self.worker_10ms.set_pause(False)
        self.worker_20ms.set_pause(False)
        self.worker_50ms.set_pause(False)
        self.worker_100ms.set_pause(False)
        self.worker_1s.set_pause(False)

    
    def closeEvent(self, event):
        '''
        重写关闭事件
        '''        
        self.stop()
        self.worker_10ms.set_running(False)
        self.worker_20ms.set_running(False)
        self.worker_50ms.set_running(False)
        self.worker_100ms.set_running(False)
        self.worker_1s.set_running(False)

        self.sig_app_exited.emit(True)
        self.pool.waitForDone(100)
        print("main window is closed.")
        event.accept()        
                
    def stop(self):
        '''
        停止线程操作
        '''   
        self.timer.stop()     

        self.worker_10ms.set_pause(True)
        self.worker_20ms.set_pause(True)
        self.worker_50ms.set_pause(True)
        self.worker_100ms.set_pause(True)
        self.worker_1s.set_pause(True) 
    
    @Slot(list)
    def menu_click(self, items):
        '''
        树形菜单项目单击
        '''        
        self.fields=self.menu.get_menu_items()
        #修改变量类的状态
        for v in self.vcs:
            if v.name in self.fields:
                v.set_enable(True)
                #数据读取队列               
                if v.name not in self.queue_vc: 
                    self.queues[v.db_data.delay].put(v)
                    self.queue_vc.append(v.name)
            else:
                v.set_enable(False)
                if v.name in self.queue_vc: 
                    #读值队列中移除v，在移动队列时进行
                    self.queue_vc.remove(v.name)  
    
    @Slot(dict)
    def menu_dblclick(self, item):
        '''
        树形菜单双击
        '''
        #新建画布
        self.log(item['name'],'新建一个绘图组件')        
        self.my_plot({'name':item['name'],'canvas':None,'msg':'new'})
        
    @Slot(dict)
    def my_plot(self, param):
        '''
        param: 0-name, 1-canvas
        双击菜单项，新增组件绘图；拖曳菜单项，在组件上增加绘图
        '''

        name=param['name']
        canvas=param['canvas']
        msg=param['msg']

        if canvas is None:
            layout = QVBoxLayout()
            layout.setSizeConstraint(QLayout.SetMinimumSize)
            canvas=MyCanvas() 
            self.curve_layout.addWidget(NavigationToolbar(canvas, self))
            self.curve_layout.addWidget(canvas)

            #新建实例，连接放下信号
            canvas.sig_item_droped.connect(self.my_plot) 

        #检测是否已在plot队列
        for vc in canvas.queue_plot:
            if vc.name==name and msg=='drop':
                print('droped but existed, skip:'+name)
                return               

        for vc in self.vcs:
            if vc.name==name:                    
                #vc.enable=True
                #布尔y设置0-1，其他格数设置为1
                if vc.db_data.data_type=='bool':
                    pass                   
                
                #实例化
                vc_plot=VcPlot(vc.name,vc.db_data.address,canvas,vc.db_data.delay,vc.db_data.data_type) 
            
                #信号连接
                #更新
                self.sig_plot_update.connect(vc_plot.update_plot)
                #改plot时间范围
                self.time_range.currentTextChanged.connect(vc_plot.set_xrange)
                #鼠标悬停更新窗口右上角xy
                vc_plot.sig_data_xy.connect(self.update_label_xy)
                #读数
                vc.sig_data_readed.connect(vc_plot.move)
                #绘画队列
                canvas.queue_plot.append(vc_plot)

                #退出循环
                break
    @Slot(str,str)
    def update_label_xy(self,tm,v):
        '''
        显示鼠标悬停处xy
        '''
        self.value_x.setText(tm)
        self.value_y.setText(v)

    @Slot(str,str)
    def log(self,name,msg):
        '''
        记录信息
        '''
        dt=datetime.datetime.now()
        msg='%s\t%s\t%s'%(dt.strftime('%Y/%m/%d %H:%M'),name,msg)
        self.log_list.addItem(msg) #log_list在main.ui中定义

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 主窗体
    main = Main()
    main.showMaximized()

    sys.exit(app.exec_())

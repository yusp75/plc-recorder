
from PySide2.QtCore import (
    QObject,
    Qt,
    Slot,
    Signal,
    QMutex,
    QModelIndex,
    QThread,
)

from PySide2.QtGui import (
    QDrag,
    QStandardItemModel,
    QPainter)

from PySide2.QtWidgets import QWidget
from snap7.types import Areas,WordLen
from struct import unpack
#from scipy import signal

import random
import snap7
import datetime
import time
import util 
import concurrent.futures
import _thread

import matplotlib as mpl
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import matplotlib.style as mplstyle

mpl.use("QtAgg")
#mplstyle.use(['dark_background', 'ggplot', 'fast'])
mpl.rcParams["path.simplify_threshold"]=0.5

mutex=QMutex()

class MyWidget(QWidget):
    '''
    重写PlotWidget拖放事件
    '''
    #拖放信号
    sig_item_droped=Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.widget_min_height=160

        self.queue_plot=[]

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
        addr=source_item.item(0, 1).text()
        #print('name:%s,address:%s'%(source_item.item(0, 0).text(),source_item.item(0, 1).text()))
        #发送放下信号
        self.sig_item_droped.emit({'name':name,'addr':addr,'widget':self,'msg':'drop'})

    def resizeEvent(self,event):
        super().resizeEvent(event)
        print('widget resized')

class MyCanvas(FigureCanvasQTAgg):
    '''
    matplotlib 自定义画布
    '''
    #拖放信号
    sig_item_droped=Signal(dict)

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        self.queue_plot=[]
        
        #super init
        super().__init__(fig)
        self.setMinimumHeight(210)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        '''
        拖放进入事件，改指示
        '''
        print('enter')
        if event.mimeData().hasFormat('application/x-qstandarditemmodeldatalist'):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        '''
        拖放放下事件
        '''
        data = event.mimeData()
        source_item = QStandardItemModel()
        source_item.dropMimeData(data, Qt.CopyAction,0,0,QModelIndex())
        name=source_item.item(0, 0).text()
        addr=source_item.item(0, 1).text()
        #print('name:%s,address:%s'%(source_item.item(0, 0).text(),source_item.item(0, 1).text()))
        #发送放下信号
        self.sig_item_droped.emit({'name':name,'addr':addr,'canvas':self,'msg':'drop'})

class Vc(QObject):
    '''
    变量类 variable class
    '''
    sig_data_readed=Signal(dict)
    sig_log_record=Signal(str,str) #信号：日志
    
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
        '''
        读数据
        '''
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
            print('Line 181 in vc.py: ',str(e),self.db_data.address,data_b)
            self.sig_log_record.emit('Vc','Line 91,%s:%s'%(self.db_data.address,data_b))
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
        return datetime.datetime.now(), data_value  
    
    def batch_read(self):
        '''
        1次读取多个变量
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
        
    def read(self):
        x,y=self.read_data()
        #发射信号
        try:
            self.sig_data_readed.emit({'x':mpl.dates.date2num(x),'y':y,'addr':self.db_data.address})
        except RuntimeError:
            print('vc read runtime error')
        
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

class VcplotThread(QThread):
    '''
    在线程更新plot
    '''

    def __init__(self,line,canvas):
        super().__init__()
        self.line=line
        self.canvas=canvas
        self.x=[]
        self.y=[]

    def set_xy(self,x,y):
        self.x=x
        self.y=y

    def run(self):
        while True:
            QThread.msleep(100)
            self.line.set_data(self.x,self.y)        
            self.canvas.axes.relim()
            self.canvas.axes.autoscale_view() 
            self.line.figure.canvas.draw()

class VcPlot(QObject):
    '''
    变量类画图
    '''
    sig_data_xy=Signal(str,str) #鼠标位置的点
    sig_update_y_value=Signal(dict) #信号：更新lengend后值

    def __init__(self,name,address,canvas,delay,data_type,live):
        super().__init__()
        self.name=name
        self.address=address
        self.delay=delay
        self.data_type=data_type
        self.canvas=canvas
        self.ax=None

        self.x=[]
        self.y=[]

        #call plot
        self.mplot(live)
    
    @Slot(dict) #x,y,addr
    def move(self,data):
        '''
        定尺寸队列，移动数据
        '''
        if self.address==data['addr']: #地址相符的更新
            if len(self.x)>=100:
                self.x=self.x[1:]
                self.y=self.y[1:]

            self.x.append(data['x'])
            if isinstance(data['y'],float):
                y=round(data['y'],2)
                self.y.append(y)
            else:
                self.y.append(data['y'])  
            
            #self.update_plot("self")
            #update legend
            #self.sig_update_y_value.emit({'p':self.ax,'value':data['y']})
            self.thread.set_xy(self.x,self.y)
            
    def mplot(self,live):
        #self.ax=self.canvas.figure.subplots()
        self.canvas.axes.legend()
        self.canvas.axes.set_autoscale_on(True)
        self.canvas.axes.grid(True)
        self.canvas.axes.set_title(self.name)
        self.canvas.axes.xaxis.set_major_formatter(mpl.dates.DateFormatter('%H:%M:%S') ) 
        
        self._line,=self.canvas.axes.plot(self.x,self.y, markevery=10) 
        if live:
            self.thread=VcplotThread(self._line,self.canvas) 
            self.thread.start()      

    @Slot(object,object)
    def item_clicked(self,obj,event):
        print(event.button())
    
    @Slot(str)
    def update_plot(self,msg):
        '''
        更新plot数据
        '''
        #print('come from %s'%msg) 
        while True:
            time.sleep(1)
            self._line.set_data(self.x,self.y)        
            self.canvas.axes.relim()
            self.canvas.axes.autoscale_view() 
            self._line.figure.canvas.draw_idle()

        

    @Slot(dict)
    def update_plot_xy(self,data):
        addr=data['addr']
        if self.address==addr:
            s1=len(data['x'])
            s2=len(data['y'])
            if s1>s2:
                print('shape mismatch: x>y')
                self.x=data['x'][:s2]
                self.y=data['y']
            elif s1<s2:
                print('shape mismatch: x<y')
                self.x=data['x']
                self.y=data['y'][:s1]
            else:
                self.x=data['x']
                self.y=data['y']
            print(len(self.x),len(self.y))
            self._line.set_data(self.x,self.y)
            self.canvas.axes.autoscale_view() 
            self.canvas.axes.relim()
            
            self._line.figure.canvas.draw_idle()
    
    def get_plot(self):
        return (self.vid,self.plot)
    
    #随机颜色
    def random_color(self): 
        '''
        随机颜色r g b
        '''       
        return (random.randint(0,255),random.randint(0,255),random.randint(0,255))

    @Slot(str)
    def set_xrange(self,range):
        seconds={
        '5s':5,
        '10s':10,
        '30s':30,
        '60s':60,
        '5min':5*60,
        '10min':10*60,
        '30min':30*60,
        }
        dt2=datetime.datetime.now()
        dt1=dt2+datetime.timedelta(seconds=-1*seconds[range])
        self.widget.setXRange(dt1.timestamp(),dt2.timestamp())
        self.ds=seconds[range]*5  # 200ms间隔


    def mouseMoved(self,event):
        '''
        p1 = win.addPlot(row=1, col=0)
        <class 'pyqtgraph.graphicsItems.PlotItem.PlotItem.PlotItem'>
        p2 = pg.plot()
        <class 'pyqtgraph.graphicsItems.PlotDataItem.PlotDataItem'>

        p1!=p2
        '''
        p=self.widget.getPlotItem()
        vb=p.vb
        mousePoint = vb.mapSceneToView(event)
        if p.sceneBoundingRect().contains(event):            
            mousePoint = vb.mapSceneToView(event)
            index = int(mousePoint.x())
            
            xv=datetime.datetime.fromtimestamp(index).strftime('%H:%M:%S')
              
            for i,x in enumerate(self.x):
                if int(x)==index:
                    #print(self.y[i])
                    try:
                        self.sig_data_xy.emit(xv,str(self.y[i])) #emit
                    except IndexError:
                        pass
                    break

            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())
        else:
            self.vLine.setPos(-1)
            self.hLine.setPos(-1)
            


from PySide2.QtCore import (
    QObject,
    Qt,
    Slot,
    Signal,
    QMutex,
    QModelIndex,
)

from PySide2.QtGui import (
    QDrag,
    QStandardItemModel,
    QPainter)
from PySide2 import QtGui

from snap7.types import Areas,WordLen
from struct import unpack

import random
import snap7
import datetime
import time
import util 
import concurrent.futures
import pyqtgraph as pg


mutex=QMutex()


class Vc(QObject):
    '''
    变量类 variable class
    '''
    data_readed=Signal(dict)
    
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
        return datetime.datetime.now().timestamp(), data_value  
    
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
            self.data_readed.emit({'x':x,'y':y,'addr':self.db_data.address})
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

class MyLegend(pg.LegendItem):
    '''
    重写legend拖放事件
    '''
    def __init__(self, size=None, offset=None, horSpacing=25, verSpacing=6,
                 pen=None, brush=None, labelTextColor=None, frame=True,
                 labelTextSize='9pt', colCount=1, sampleType=None, **kwargs):
        pg.LegendItem.__init__(self,**kwargs)

    def mouseDragEvent(self, event):
        pos=event.pos()
        for item in self.items: 
            #print(pos, item[1].geometry())           
            if item[1].geometry().contains(pos):
                print('in')
            #print(self.layout.geometry())
        super().mouseDragEvent(event)

    def paintEvent(self, event):
        p=QPainter(self)
        p.setPen(self.pen)
        p.setBrush(self.brush)
        p.drawRect(self.items[0][1].geometry())

class MyPlotWidget(pg.PlotWidget):
    '''
    重写PlotWidget拖放事件
    '''
    #拖放信号
    item_droped=Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.widget_min_height=160
        self.setBackground('w') 
        self.showGrid(x=True,y=True)
        self.setAxisItems({'bottom': pg.DateAxisItem()})
        self.setMinimumHeight(self.widget_min_height) 
        #不显示上下文菜单
        self.setContextMenuActionVisible('Downsample',False)
        self.setContextMenuActionVisible('Alpha',False)
        self.setContextMenuActionVisible('Points',False)
        #记录新建、拖放的曲线
        self.queue_plot=[]

        axis_y=pg.AxisItem(orientation='left')
        axis_y.setTickSpacing(0.5,1)
        self.setAxisItems({'left':axis_y})

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
        self.item_droped.emit({'name':name,'addr':addr,'widget':self,'msg':'drop'})


class VcPlot(QObject):
    '''
    变量类画图
    '''
    sig_data_xy=Signal(str,str) #鼠标位置的点

    def __init__(self,name,address,widget,delay,data_type):
        super().__init__()
        self.name=name
        self.address=address
        self.delay=delay
        self.data_type=data_type
        self.widget=widget
        self.plot=None
        self.color=self.random_color()
        self.pen=pg.mkPen(color=self.color, width=1, style=Qt.SolidLine)
        self.brush=pg.mkBrush(255,0,0)
        self.x=[]
        self.y=[]
        self.ds=1
        
        if self.delay in ['10ms','20ms','50ms','100ms']:
            factor=int(self.delay[:-2])
            self.ds=1000/(factor*2) # 1秒2个值

        #游丝
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)

        #call plot
        self.mplot()
    
    @Slot(dict) #x,y,addr
    def move(self,data):
        if self.address==data['addr']: #地址相符的更新
            if len(self.x)>1000:
                self.x[:-1]=self.x[1:]
                self.y[:-1]=self.y[1:]
            self.x.append(data['x'])
            self.y.append(data['y'])            
            
    def mplot(self):
        self.plot=self.widget.plot(self.x,self.y,name=self.name,pen=self.pen,symbol='+',symbolSize=1,symbolBrush=('b'))
        self.plot.curve.setClickable(True)

        #游丝
        self.widget.addItem(self.vLine, ignoreBounds=True)
        self.widget.addItem(self.hLine, ignoreBounds=True)        
        self.widget.getPlotItem().scene().sigMouseMoved.connect(self.mouseMoved)
        
        plotItem=self.widget.getPlotItem()      
        pen=pg.mkPen(255,0,0)
        brush=pg.mkBrush(0,255,0)
        legend=MyLegend(pen=pen,brush=brush,frame=True)
        if plotItem.legend is None:
            plotItem.legend=legend
            legend.addItem(self.plot,self.name) 
            legend.setParentItem(plotItem)

        elif len(plotItem.legend.items)>=1:
            plotItem.legend.removeItem(self.name)
            plotItem.legend.addItem(self.plot,self.name)

        self.plot.sigClicked.connect(self.item_clicked)
        self.widget.getViewBox().addItem(self.plot)        

    @Slot(object,object)
    def item_clicked(self,obj,event):
        print(event.button())
    
    @Slot(str)
    def update_plot(self,msg):
        '''
        更新plot数据
        '''
        #print('come from %s'%msg)
        self.plot.setDownsampling(ds=self.ds,auto=True,method='peak')
        self.plot.setClipToView(True)        
        self.plot.setData(self.x,self.y)

    @Slot(dict)
    def update_plot_xy(self,data):
        addr=data['addr']
        if self.address==addr:
            self.x=data['x']
            self.y=data['y']
            self.plot.setData(self.x,self.y)
    
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
                    self.sig_data_xy.emit(xv,str(self.y[i])) #emit
                    break

            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())

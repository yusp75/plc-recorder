from PySide2.QtWidgets import QApplication, QMainWindow, QWidget,QMessageBox
from PySide2.QtGui import QPen
from PySide2.QtCore import Qt,Slot,Signal
from PySide2.QtGui import QStandardItemModel,QStandardItem

from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from db import Db
from ymenu import Menu
from vc import MyPlotWidget,VcPlot,Vc

import sys
import os
import util
import datetime
import random

        
uiclass, baseclass = pg.Qt.loadUiType("curve.ui")

class Curve(uiclass, baseclass):
    '''
    历史曲线
    '''
    plot_update=Signal(str)

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle('历史曲线')
    
        # 查询按钮
        self.btnQuery.clicked.connect(self.query_data)
        self.btnNow.clicked.connect(self.time_now)
        #初始查询时间
        self.time_now()        
    
        self.menu_items=[] #菜单项集
        self.menu=Menu(self.tree)
        self.menu.item_changed.connect(self.menu_click)
        #连接双击信号
        self.menu.item_dblclicked.connect(self.menu_dblclick)
        self.fields=[] #字段

        self.queue_plot=[]
        self.vcs=[]

    
    #设置查询起始时间
    def time_now(self):            
        dt=datetime.datetime.now()
        self.dt1.setDateTime(dt+datetime.timedelta(minutes=-1))
        self.dt2.setDateTime(dt)
    
    #随机颜色
    def random_color(self):        
        r=random.randint(0,255)
        g=random.randint(0,255)
        b=random.randint(0,255)
        return (r,g,b)
    

    #绘画
    def plot(self,x,y,ymin,ymax):
        self.widget.setTitle('Curve')
        self.widget.addLegend()
        self.widget.showGrid(x=True,y=True) 
        self.widget.setYRange(ymin,ymax,padding=0)
        self.widget.setAxisItems({'bottom': pg.DateAxisItem()})
        
        pen_color=self.random_color()
        pen = pg.mkPen(color=pen_color, width=1, style=Qt.SolidLine)
        self.widget.plot(x, y, pen=pen, symbol='+', symbolSize=3, symbolBrush=('b'))
    
    #查询数据    
    def query_data(self):
        print('query_data...')
        dt1=self.dt1.dateTime().toPython()
        dt2=self.dt2.dateTime().toPython()

        m_db=Db()
        if len(self.fields)==0:
            msgBox=QMessageBox();
            msgBox.setText("查询变量表为空");
            msgBox.exec();
            return

        names,data=m_db.query(dt1,dt2,self.fields)
        #print(data)
        for d in data:
            lv=d['v']            
            mn=min(lv)
            mx=max(lv)
            dtype=d['t']

            #更新数据到plot
            for plot in self.queue_plot:
                if d['nm']==plot.name:
                    plot.x=d['tm']
                    plot.y=d['v']
                    plot.plot.setdata(x,y)

        self.emit(plot_update)
            
    
    @Slot(list)
    def menu_click(self, items):
        '''
        菜单项选中
        '''
        #print('curve:',items)
        self.fields=self.menu.get_menu_items()
        
    

    @Slot(dict)
    def my_plot(self, param):
        '''
        param: 0-name, 1-widget
        双击菜单项，新增组件绘图；拖曳菜单项，在组件上增加绘图
        '''

        name=param['name']
        address=param['addr']
        widget=param['widget']
        msg=param['msg']
        print(param['msg'])

        if widget is None:
            widget=MyPlotWidget() 
            #新建widget要放到layout上
            self.layout.addWidget(widget)
            #新建实例，连接放下信号
            widget.item_droped.connect(self.my_plot) 

        #检测是否已在plot队列
        for plot in self.queue_plot:
            if plot.name==name and msg=='drop':
                print('droped but existed, skip:'+name)
                return               

        #for vc in self.vcs:
        #    if vc.name==name:                    
                #vc.enable=True
                #布尔y设置0-1，其他格数设置为1
        #        if vc.db_data.data_type=='bool':
        #            widget.setYRange(0,1,padding=0)                    
                #标题：名称+地址
        title=widget.windowTitle()
        widget.setTitle('%s %s:%s'%(title,name,address))
        
        #实例化
        vc_plot=VcPlot(name,address,widget)               
        #信号连接
        #更新
        self.plot_update.connect(vc_plot.update_plot)              
        #绘画队列
        self.queue_plot.append(vc_plot)
              
                #退出循环
        #        break

    @Slot(str)
    def menu_dblclick(self, item):
        '''
        树形菜单双击
        '''
        #新建plotwidget
        name=item['name']
        addr=item['addr']
        self.my_plot({'name':name, 'addr':addr,'widget':None,'msg':'new'})     
               
  
if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Curve()
    w.show()
    app.exec_()
    
from PySide2.QtWidgets import QApplication, QMainWindow, QWidget
from PySide2.QtGui import QPen
from PySide2.QtCore import Qt, Slot
from PySide2.QtGui import QStandardItemModel,QStandardItem

from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from db import Db
from ymenu import Menu

import sys
import os
import util
import datetime
import random

        
uiclass, baseclass = pg.Qt.loadUiType("curve.ui")

class Curve(uiclass, baseclass):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
    
        # 查询按钮
        self.btnQuery.clicked.connect(self.query_data)
        self.btnNow.clicked.connect(self.time_now)
        #初始查询时间
        self.time_now()
        
        # widget        
        self.widget.setBackground('w')
        self.menu_items=[] #菜单项集
        self.menu=Menu(self.tree)
        self.menu.item_changed.connect(self.menu_click)
        self.fields=[]
    
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
        names,data=m_db.query(dt1,dt2,self.fields)
        #print(data)
        for d in data:
            lv=list(d.values())[0]            
            mn=min(lv[0])
            mx=max(lv[0])
            dtype=lv[1]
            if dtype=='bool':
                self.plot(lv[0],lv[1],0,2)
            else:
                self.plot(lv[0],lv[1],mn,mx)
    
    @Slot(list)
    def menu_click(self, items):
        print('curve:',items)
        self.fields=self.menu.get_menu_items()
   
  
if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Curve()
    w.show()
    app.exec_()
    
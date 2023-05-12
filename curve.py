from PySide2.QtWidgets import QApplication, QMainWindow, QWidget,QMessageBox
from PySide2.QtGui import QPen
from PySide2.QtCore import Qt,Slot,Signal
from PySide2.QtGui import QStandardItemModel,QStandardItem

from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from db import Db
from ymenu import Menu
from vc import VcPlot,Vc

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
    plot_update=Signal(dict) #有别于main的信号

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
        m_db.close()
        #print(data)
        for d in data:
            #更新plot数据
            self.plot_update.emit({'addr':d['addr'],'x':d['tm'],'y':d['v']}) 
    
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
            widget=QWidget() 
            #新建widget要放到layout上
            self.layout.addWidget(widget)
            #新建实例，连接放下信号
            widget.sig_item_droped.connect(self.my_plot) 

        #检测是否已在plot队列
        for plot in widget.queue_plot:
            if plot.name==name and msg=='drop':
                print('droped but existed, skip:'+name)
                return               

        title=widget.windowTitle()
        widget.setTitle('%s %s:%s'%(title,name,address))
        
        #实例化
        vc_plot=VcPlot(name,address,widget,None,None)               
        #信号连接
        #更新
        self.plot_update.connect(vc_plot.update_plot_xy)              
        #绘画队列
        widget.queue_plot.append(vc_plot)

    @Slot(str)
    def menu_dblclick(self, item):
        '''
        树形菜单双击
        '''
        #新建plotwidget
        name=item['name']
        addr=item['addr']
        self.my_plot({'name':name,'addr':addr,'widget':None,'msg':'new'})     
               
  
if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Curve()
    w.show()
    app.exec_()
    
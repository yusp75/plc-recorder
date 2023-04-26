from PySide2.QtGui import QStandardItemModel,QStandardItem
from PySide2.QtCore import Signal, QObject
from myaml import Myaml

import os

class Menu(QObject):
    '''
    菜单定义
    '''
    #信号定义
    item_changed=Signal(list)
    item_dblclicked=Signal(dict)
    
    def __init__(self,tree_widget,checkable=True):
        super().__init__()
        self.model=QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['name','address',])        
        self.model.setRowCount(0)
        root=self.model.invisibleRootItem()
        
        self.tree=tree_widget
        self.tree.setModel(self.model)

        self.tree.clicked.connect(self.tree_clicked)
        self.tree.doubleClicked.connect(self.tree_dblclicked)  #信号待更换
        
        self.menu_items=[] #菜单项集        
        
        # 迭代self.dbs，添加子节点
        dbs=self.read_var()
        for d in dbs:
            item=QStandardItem(d.name)
            item2=QStandardItem(d.address)
            item.setCheckable(checkable)
            
            root.appendRow([item,item2])
        self.tree.expandAll()
   
    def tree_clicked(self,model_index):
        '''
        菜单项选中
        '''
        row=model_index.row()
        item=self.model.item(row)
        checked=item.checkState()
        #增减
        if checked:
            if item.text() not in self.menu_items:
                self.menu_items.append(item.text())
        else:
            if item.text() in self.menu_items:
                    self.menu_items.remove(item.text())                    

        #print('menu 单击',self.menu_items)
        self.item_changed.emit(self.menu_items)

    def tree_dblclicked(self,model_index):
        '''
        菜单树双击
        '''
        row=model_index.row()
        item=self.model.item(row)
        item2=self.model.item(row,1)
        if item.text() not in self.menu_items:
            self.menu_items.append(item.text())
        
        #print('menu 双击',item2.text())
        #self.item_changed.emit(self.menu_items)
        self.item_dblclicked.emit({'name':item.text(),'addr':item2.text()})
        
    # 扫描var目录
    def read_var(self):        
        files=os.listdir('var')
        # print(files)
        list_var=[]
        for file in files:
            if file.endswith('yaml'):
                # 解析
                myaml=Myaml('var/'+file)
                var = myaml.parse()
                list_var=list_var+var
        return list_var  
        
    #getter for 菜单项集
    def get_menu_items(self):
        return self.menu_items

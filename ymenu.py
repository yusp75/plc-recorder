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
    item_dblclicked=Signal(str)
    
    def __init__(self, tree_widget):
        super().__init__()
        self.model=QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['name','address',])        
        self.model.setRowCount(0)
        root=self.model.invisibleRootItem()
        
        self.tree=tree_widget
        self.tree.setModel(self.model)
        self.tree.doubleClicked.connect(self.tree_clicked)  #信号待更换
        
        self.menu_items=[] #菜单项集        
        
        # 迭代self.dbs，添加子节点
        dbs=self.read_var()
        for d in dbs:
            item=QStandardItem(d.name)
            item2=QStandardItem(d.address)
            item.setCheckable(False)
            
            root.appendRow([item,item2])
        self.tree.expandAll()
        
    def tree_clicked(self,model_index):
        '''
        菜单树点击
        '''
        row=model_index.row()
        #col=item.col()
        item=self.model.item(row)
        if item.text() not in self.menu_items:
            self.menu_items.append(item.text())
        
        #print(self.menu_items)
        self.item_changed.emit(self.menu_items)
        self.item_dblclicked.emit(item.text())
        
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

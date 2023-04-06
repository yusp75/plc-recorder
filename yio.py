from PySide2.QtCore import (
    QFile,
    QIODevice,
    QObject
)
from PySide2.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QMessageBox,
    QPushButton, 
    QLineEdit, 
    QTableWidget, 
    QHeaderView,
    QTableWidgetItem
)
from snap7.types import Areas
from myaml import Myaml

import util
import sys
import snap7
import yaml
import os


AREAS_TYPE={Areas.PE:'Areas.PE',Areas.PA:'Areas.PE',Areas.PA:'Areas.PE'
            ,Areas.MK:'Areas.MK',Areas.DB:'Areas.DB',}

class Io(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.window = util.get_window('io.ui')
        # 标签
        self.et_ip = self.window.findChild(QLineEdit, 'ip')
        self.et_slot = self.window.findChild(QLineEdit, 'slot')
        self.label_ok = self.window.findChild(QLabel, 'labelOk')
        self.label_num = self.window.findChild(QLabel, 'lblNum')
        # 按钮
        self.pb_test = self.window.findChild(QPushButton, 'pbTest')
        self.pb_test.clicked.connect(self.link_plc)
        self.pb_refresh = self.window.findChild(QPushButton, 'btnRefresh')
        self.pb_refresh.clicked.connect(self.read_var)
        self.pb_cancel = self.window.findChild(QPushButton, 'pbCancel')
        self.pb_cancel.clicked.connect(self.window.close)

        self.client=None
        self.ip='192.168.0.10'
        self.slot='3'
        self.read_plc()
        
        self.pb_apply = self.window.findChild(QPushButton, 'pbApply')
        # self.pb_apply.clicked.connect(self.update_vbt)
        
        # 表格
        self.decribe_tbl()
        # 导入变量
        self.list_var=[]
        self.read_var()

    # 测试plc连接
    def link_plc(self):
        client = snap7.client.Client()
        try:
            client.connect(self.et_ip.text(), 0, int(self.et_slot.text()))
            if client.get_connected():
                # 设置连接指示颜色
                self.label_ok.setStyleSheet('background-color:#00ff00')
                self.client=client
        except RuntimeError as e:
            print('link plc error:',str(e))
            client.destroy()
    
    # plc连接参数
    def read_plc(self):
        try:
            with open('conf/plc.yaml') as f:
                data=yaml.load(f, Loader=yaml.FullLoader)
                self.ip=data['ip']
                self.slot=data['slot']
        except Exception as e:
            print('yio,读PLC连接参数错：', e)
            
        self.et_ip.setText(self.ip)
        self.et_slot.setText(str(self.slot))
        # test
        self.link_plc()
        
    def decribe_tbl(self):
        # 表格格式描述
        self.table1 = self.window.findChild(QTableWidget, 'table1')
        self.table1.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table1.setColumnWidth(7, 20)
        self.table1.setHorizontalHeaderLabels(('device', 'address', 'area', 'number','start','size','bit'))

    def show(self):
        self.window.show()
    
    def read_var(self):
        # 扫描var目录
        files=os.listdir('var')
        # print(files)
        
        for file in files:
            if file.endswith('yaml'):
                # 解析
                myaml=Myaml('var/'+file)
                var = myaml.parse()
                self.list_var=self.list_var+var
        # print('var list:', self.list_var)
        # 写到表格
        self.label_num.setText(str(len(self.list_var)))
        # self.table1.setRowCount(len(self.list_var))
        for i, v in enumerate(var):
            cell=QTableWidgetItem(v.device)
            self.table1.setItem(i,0,cell)
            cell=QTableWidgetItem(v.address)
            self.table1.setItem(i,1,cell)
            cell=QTableWidgetItem(AREAS_TYPE[v.areas])
            self.table1.setItem(i,2,cell)
    
    def get_connected(self):
        is_ok=True
        if (self.client is None) or (not self.client.get_connected()):
            is_ok=False
        return is_ok
    

if __name__ == '__main__':
    app = QApplication(sys.argv)
    io = Io()
    io.show()

    sys.exit(app.exec_())
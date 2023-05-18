from PySide2.QtCore import (
    QFile,
    QIODevice,
    QObject
)
from PySide2.QtUiTools import QUiLoader
from myaml import Myaml

import os


def get_window(file):
    ui = QFile(file)
    if not ui.open(QIODevice.ReadOnly):
        print('Cannot open {}: {}'.format(file, ui.errorString()))
        sys.exit(-1)
    loader = QUiLoader()
    w = loader.load(ui)
    ui.close()
    if not w:
        print(loader.errorString())
        sys.exit(-1)
    return w


def read_var():
    '''
    扫描var目录读取变量
    '''        
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
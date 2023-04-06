from PySide2.QtCore import (
    QFile,
    QIODevice,
    QObject
)
from PySide2.QtUiTools import QUiLoader

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
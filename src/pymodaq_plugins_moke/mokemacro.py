import sys
from PyQt5 import QtWidgets
from pymodaq.daq_utils.gui_utils import DockArea
from pymodaq.daq_viewer.daq_viewer_main import DAQ_Viewer

def main():
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Viewer')
    prog = DAQ_Viewer(area, title="MokeMacro", DAQ_type='DAQ1D')
    prog.detector = 'MokeMacro'
    prog.init_det()
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

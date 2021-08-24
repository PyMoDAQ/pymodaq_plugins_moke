import sys
from PyQt5 import QtWidgets
from pymodaq.daq_utils.gui_utils import DockArea
from pymodaq.dashboard import DashBoard
from pymodaq_plugins_moke.utils.led_control import LedControl

def main():
    from pymodaq.daq_utils.daq_utils import get_set_preset_path
    from pymodaq.daq_utils.gui_utils import DockArea
    from pathlib import Path
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')

    prog = DashBoard(area)
    file = Path(get_set_preset_path()).joinpath("microMOKE.xml")
    if file.exists():
        prog.set_preset_mode(file)
        #prog.load_scan_module()
    else:
        msgBox = QtWidgets.QMessageBox()
        msgBox.setText(f"The default file specified in the configuration file does not exists!\n"
                       f"{file}\n"
                       f"Impossible to load the DAQ_Scan Module")
        msgBox.setStandardButtons(msgBox.Ok)
        ret = msgBox.exec()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
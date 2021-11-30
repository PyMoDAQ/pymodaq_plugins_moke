import numpy as np

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtWidgets import QWidget
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils import gui_utils as gutils
from pyqtgraph.widgets.SpinBox import SpinBox


class ManualActuation(gutils.CustomApp):
    def __init__(self, dockarea, Npush=3):
        super().__init__(dockarea)
        self.Npush = Npush
        self.setup_ui()

    def connect_things(self):
        pass

    def setup_actions(self):
        '''
        subclass method from ActionManager
        '''
        pass

    def setup_docks(self):
        '''
        subclass method from CustomApp
        '''
        self.dock = gutils.Dock('ManualCurrent', size=(350, 350))
        self.dockarea.addDock(self.dock, 'left')
        widget = QtWidgets.QWidget()
        hlayout = QtWidgets.QHBoxLayout()
        vrel_layout = QtWidgets.QVBoxLayout()
        vabs_layout = QtWidgets.QVBoxLayout()
        widget.setLayout(hlayout)

        vrel_layout.addWidget(QtWidgets.QLabel('Relative'), 0, alignment=QtCore.Qt.AlignHCenter)
        vabs_layout.addWidget(QtWidgets.QLabel('Absolute'), 0, alignment=QtCore.Qt.AlignHCenter)

        self._epsilon = gutils.EditPushRel('go_to', '\u03B5')
        vrel_layout.addWidget(self._epsilon, 100, alignment=QtCore.Qt.AlignHCenter)

        self._abs_pushs = []
        for ind_abs in range(self.Npush):
            self._abs_pushs.append(gutils.EditPush('go_to'))
            vabs_layout.addWidget(self._abs_pushs[-1], 100, alignment=QtCore.Qt.AlignHCenter)

        line = QtWidgets.QFrame()
        line.setFrameShape(line.VLine)

        hlayout.addLayout(vrel_layout)
        hlayout.addWidget(line)
        hlayout.addLayout(vabs_layout)

        widget.setMaximumWidth(300)
        widget.setMaximumHeight(220)
        self.dock.addWidget(widget)

    @property
    def epsilon(self):
        return self._epsilon_edit.value()

    @epsilon.setter
    def espilon(self, value):
        return self._epsilon_edit.setValue(value)

def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    dockarea = gutils.DockArea()
    prog = ManualActuation(dockarea)
    dockarea.show()
    sys.exit(app.exec_())


if __name__ == '__main__':

    main()

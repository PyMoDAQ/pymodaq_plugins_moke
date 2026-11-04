from typing import List, TYPE_CHECKING

import numpy as np

from pymodaq_gui.utils.dock import Dock, DockArea
from pymodaq_gui.managers.parameter_manager import ParameterManager, Parameter

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtWidgets import QWidget
from pymodaq_utils import utils as utils

from pymodaq.utils.scanner.scanners._1d_scanners import Scan1DSparse
from pymodaq_gui.plotting.data_viewers.viewer1D import Viewer1D
from pymodaq.utils.data import DataActuator
from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq_gui.messenger import dialog


class StepsSequencer(ParameterManager, QtCore.QObject):

    scanner_parameter = QtCore.Signal(Parameter)
    params = [dict(title='Npts', name='npts', type='int', readonly=True),
              dict(title='', label='Send Points', name='send_points', type='bool_push'),
              dict(title='', label='Show Points', name='show_points', type='bool_push'),]

    def __init__(self, dockarea: DockArea, actuator: DAQ_Move):
        ParameterManager.__init__(self)
        QtCore.QObject.__init__(self)
        self.actuator = actuator
        self.actuator_name = actuator.title
        self.dockarea = dockarea
        self.scanner = Scan1DSparse([actuator])
        self.setup_docks()
        self.scanner.settings.child('parsed_string').sigValueChanged.connect(self.value_changed)

    def setup_docks(self):
        '''
        subclass method from CustomApp
        '''
        widget = QtWidgets.QWidget()
        widget.setLayout(QtWidgets.QVBoxLayout())

        widget.layout().addWidget(self.settings_tree)
        widget.layout().addWidget(self.scanner.settings_tree)

        self.dock = Dock('Steps Sequencer', size=(350, 350))
        self.dockarea.addDock(self.dock, 'left')
        self.dock.addWidget(widget, 10)
        self.settings_tree.setMinimumSize(350, 100)

    def emit_positions(self):
        self.scanner_parameter.emit(self.scanner.settings.child('parsed_string'))

    def value_changed(self, param):
        if param.name() == 'parsed_string':
            self.evaluate_nsteps()
        elif param.name() == 'send_points':
            if param.value():
                self.emit_positions()
                param.setValue(False)
        elif param.name() == 'show_points':
            if param.value():
                self.show_positions()
                param.setValue(False)

    def show_positions(self):
        widget = QtWidgets.QWidget()
        viewer = Viewer1D(widget)
        self.scanner.set_scan()
        dwa = DataActuator(self.actuator_name, data=[np.atleast_1d(np.squeeze(self.scanner.positions))])
        viewer.show_data(dwa)
        dialog('Positions to be send to Tabular Scan', '', widget)

    def evaluate_nsteps(self):
        Nsteps = self.scanner.evaluate_steps()
        self.settings.child('npts').setValue(Nsteps)

    def update_steps_calculation(self):
        init = False
        values = np.array([])
        for ind, data in enumerate(self._table_model.raw_data):
            if not init and self._table_model.is_checked(ind):
                values = utils.linspace_step(*data)
                init = True
            elif self._table_model.is_checked(ind):
                values = np.concatenate((values, utils.linspace_step(*data)))
        return values

    @property
    def view(self):
        return self._table_view


def print_positions(param: Parameter):
    print(param.value())


def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()
    move = DAQ_Move(widget)
    widget.show()
    dockarea = DockArea()
    prog = StepsSequencer(dockarea, move)
    prog.scanner_parameter.connect(print_positions)
    dockarea.show()
    sys.exit(app.exec_())


if __name__ == '__main__':

    main()

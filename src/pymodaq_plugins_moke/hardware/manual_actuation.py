from qtpy import QtWidgets, QtCore

from pymodaq_gui.utils.custom_app import CustomApp
from pymodaq_gui.utils.dock import Dock, DockArea


from pymodaq_gui import utils as gutils
from pymodaq.control_modules.move_utility_classes import MoveCommand
from pymodaq_plugins_moke import config


class ManualActuation(CustomApp):
    actuation_signal = QtCore.Signal(MoveCommand)

    def __init__(self, dockarea, absolute_values=[0.1, 0.2, 0.8], relative_value=0.1):
        super().__init__(dockarea)
        self.absolute_values = absolute_values
        self.relative_value = relative_value
        self.Npush = len(absolute_values)
        self.setup_ui()

    def connect_things(self):
        pass

    def setup_actions(self):
        '''
        overridden method from ActionManager
        '''
        pass

    def setup_docks(self):
        '''
        overridden method from CustomApp
        '''
        self.dock = Dock('ManualCurrent', size=(350, 350))
        self.dockarea.addDock(self.dock, 'left')
        widget = QtWidgets.QWidget()
        hlayout = QtWidgets.QHBoxLayout()
        vrel_layout = QtWidgets.QVBoxLayout()
        vabs_layout = QtWidgets.QVBoxLayout()
        widget.setLayout(hlayout)

        vrel_layout.addWidget(QtWidgets.QLabel('Relative'), 0, alignment=QtCore.Qt.AlignHCenter)
        vabs_layout.addWidget(QtWidgets.QLabel('Absolute'), 0, alignment=QtCore.Qt.AlignHCenter)

        self._epsilon = gutils.EditPushRel('go_to', text='\u03B5', ini_value=self.relative_value)
        vrel_layout.addWidget(self._epsilon, 100, alignment=QtCore.Qt.AlignHCenter)
        self._epsilon.clicked.connect(self.emit_actuation)

        self._abs_pushs = []
        for ind_abs in range(self.Npush):
            self._abs_pushs.append(gutils.EditPush('go_to', ini_value=self.absolute_values[ind_abs]))
            vabs_layout.addWidget(self._abs_pushs[-1], 100, alignment=QtCore.Qt.AlignHCenter)
            self._abs_pushs[-1].clicked.connect(self.emit_actuation)

        line = QtWidgets.QFrame()
        line.setFrameShape(line.VLine)

        hlayout.addLayout(vrel_layout)
        hlayout.addWidget(line)
        hlayout.addLayout(vabs_layout)

        widget.setMaximumWidth(300)
        widget.setMaximumHeight(220)
        self.dock.addWidget(widget)

    def emit_actuation(self, editpushinfo):
        """
        emit the value to set in the possibly connected actuators
        """
        self.actuation_signal.emit(MoveCommand(move_type=editpushinfo.type,
                                               value=editpushinfo.value))

    @property
    def epsilon(self):
        return self._epsilon_edit.value()

    @epsilon.setter
    def espilon(self, value):
        return self._epsilon_edit.setValue(value)


@QtCore.Slot(dict)
def print_actuation(actuation: MoveCommand):
    print(f'Move {actuation.move_type} with {actuation.value} magnitude')


def main():
    import sys
    absolute_current_values = config('micro', 'actuation', 'absolute_current_values')
    relative_value = config('micro', 'actuation', 'relative_value')

    app = QtWidgets.QApplication(sys.argv)
    dockarea = DockArea()
    prog = ManualActuation(dockarea, absolute_current_values, relative_value)
    prog.actuation_signal.connect(print_actuation)
    dockarea.show()
    sys.exit(app.exec_())


if __name__ == '__main__':

    main()

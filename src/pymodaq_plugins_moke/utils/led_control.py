import sys
from PyQt5 import QtWidgets, QtCore
from pyqtgraph.parametertree import Parameter, ParameterTree
from pymodaq.resources.QtDesigner_Ressources import QtDesigner_ressources_rc
from pymodaq.daq_utils.parameter.pymodaq_ptypes import SliderSpinBox, QLED
from pymodaq.daq_utils import gui_utils as gutils
from collections import OrderedDict

from pymodaq_plugins_daqmx.hardware.national_instruments import daq_NIDAQmx
from pymodaq_plugins_daqmx.hardware.national_instruments.daqmx import DAQmx, DAQ_analog_types, DAQ_thermocouples,\
    DAQ_termination, Edge, DAQ_NIDAQ_source, \
    ClockSettings, AIChannel, Counter, AIThermoChannel, AOChannel, TriggerSettings, DOChannel, DIChannel



class LedControl(QtCore.QObject):

    def __init__(self, area):
        self.area = area
        self.led_manual_control = None
        self.dock_manual = None
        self.dock_sequence = None
        self.setupUi()

    def setupUi(self):

        self.dock_manual = gutils.Dock('LED Manual')
        self.dock_sequence = gutils.Dock('LED Sequences')

        self.area.addDock(self.dock_manual, 'top')
        self.area.addDock(self.dock_sequence, 'below', self.dock_manual)

        widget_manual = QtWidgets.QWidget()
        self.led_manual_control = ManualLedControl(widget_manual)
        self.dock_manual.addWidget(widget_manual)

        self.dock_manual.raiseDock()


class ManualLedControl(QtCore.QObject):
    leds_value = QtCore.pyqtSignal(dict)

    def __init__(self, parent_widget):
        super().__init__()
        self.parent = parent_widget
        self.setupUi()
        self.connecting()

    def setupUi(self):
        self.leds = OrderedDict([])
        scale = 2
        self.leds['top'] = QLED(scale=scale)
        self.leds['bottom'] = QLED(scale=scale)
        self.leds['left'] = QLED(scale=scale)
        self.leds['right'] = QLED(scale=scale)

        self.sliders = OrderedDict([])
        self.sliders['top'] = SliderSpinBox(bounds=[0, 3.5], value=0.)
        self.sliders['bottom'] = SliderSpinBox(bounds=[0, 3.5], value=0.)
        self.sliders['left'] = SliderSpinBox(bounds=[0, 3.5], value=0.)
        self.sliders['right'] = SliderSpinBox(bounds=[0, 3.5], value=0.)

        widgets = OrderedDict([])
        widgets['top'] = QtWidgets.QWidget()
        widgets['bottom'] = QtWidgets.QWidget()
        widgets['left'] = QtWidgets.QWidget()
        widgets['right'] = QtWidgets.QWidget()

        for ind, key in enumerate(self.leds):
            widgets[key].setLayout(QtWidgets.QHBoxLayout())
            widgets[key].layout().addWidget(self.leds[key])
            widgets[key].layout().addWidget(self.sliders[key])

        self.parent.setLayout(QtWidgets.QGridLayout())

        self.parent.layout().addWidget(widgets['top'], 0, 2, )
        self.parent.layout().addWidget(widgets['left'], 1, 1, )
        self.parent.layout().addWidget(widgets['right'], 1, 3, )
        self.parent.layout().addWidget(widgets['bottom'], 2, 2, )

        self.check_all_cb = QtWidgets.QCheckBox('All/None')
        self.offset_all_slider = SliderSpinBox(bounds=[0., 3.5], value=0.)
        self.offset_all_slider.insert_widget(QtWidgets.QLabel('Offset all:'))
        self.parent.layout().addWidget(self.check_all_cb, 0, 0)
        self.parent.layout().addWidget(self.offset_all_slider, 2, 0)

    def connecting(self):
        for ind, key in enumerate(self.sliders):
            self.leds[key].value_changed.connect(lambda: self.emit_led_values())
            self.sliders[key].sigValueChanged.connect(lambda: self.emit_led_values())

        self.check_all_cb.clicked.connect(lambda: self.activate_leds())
        self.offset_all_slider.sigValueChanged.connect(lambda: self.emit_led_values())

    def activate_leds(self, state=None):
        if state is None:
            state = self.check_all_cb.isChecked()

        for led in self.leds:
            self.leds[led].set_as(state)

    def display_state(self):
        for ind, key in enumerate(self.leds):
            print(f'{key} LED {"on" if self.leds[key].get_state() else "off"} with value {self.sliders[key].value()}')

    def emit_led_values(self):
        offset = self.offset_all_slider.value()
        leds_value = dict([])
        for key in self.sliders:
            leds_value[key] = {f'{key}_val': self.sliders[key].value() + offset,
                               f'{key}_act': self.leds[key].get_state()}

        self.leds_value.emit(leds_value)

def main():
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = gutils.DockArea()
    win.setCentralWidget(area)
    LedControl(area)

    win.setWindowTitle('LEDControls')
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

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
        self.led_daqmx = None
        self.setupUi()

    def setupUi(self):

        dock_manual = gutils.Dock('LED Manual')
        dock_sequence = gutils.Dock('LED Sequences')
        dock_settings = gutils.Dock('LED Settings')
        self.area.addDock(dock_manual, 'top')
        self.area.addDock(dock_sequence, 'below', dock_manual)
        self.area.addDock(dock_settings, 'below', dock_sequence)

        widget_manual = QtWidgets.QWidget()
        self.led_manual_control = ManualLedControl(widget_manual)
        dock_manual.addWidget(widget_manual)
        
        widget_settings = QtWidgets.QWidget()
        self.led_daqmx = LedDAQmx(widget_settings)
        dock_settings.addWidget(widget_settings)

        dock_manual.raiseDock()


class LedDAQmx:
    params = [
        {'title': 'LEDs:', 'name': 'ao_leds', 'type': 'group', 'expanded': True, 'children': [
            {'title': 'Top LED:', 'name': 'ao_top_led', 'type': 'list',
             'values': DAQmx.get_NIDAQ_channels(source_type='Analog_Output'), 'value': 'cDAQ1Mod3/ao0'},
            {'title': 'Left LED:', 'name': 'ao_left_led', 'type': 'list',
             'values': DAQmx.get_NIDAQ_channels(source_type='Analog_Output'), 'value': 'cDAQ1Mod3/ao1'},
            {'title': 'Right LED:', 'name': 'ao_right_led', 'type': 'list',
             'values': DAQmx.get_NIDAQ_channels(source_type='Analog_Output'), 'value': 'cDAQ1Mod3/ao2'},
            {'title': 'Bottom LED:', 'name': 'ao_bottom_led', 'type': 'list',
             'values': DAQmx.get_NIDAQ_channels(source_type='Analog_Output'), 'value': 'cDAQ1Mod3/ao3'},
            ]},
        {'title': 'Camera Trigger:', 'name': 'di_camera', 'type': 'list',
         'values': DAQmx.get_NIDAQ_channels(source_type='Digital_Input'), 'value': 'cDAQ1Mod4/port0/line0'},
        ]
    
    def __init__(self, parent_widget):
        super().__init__()
        self.parent = parent_widget
        self.settings_tree = None
        self.settings = None
        self.channel_di = None
        self.channels_led = None

        self.setupUI()
        self.controller = dict(ao=DAQmx(), di=DAQmx())

        self.update_tasks()

    def update_tasks(self):

        self.channel_di = DIChannel(name=self.settings.child('di_camera').value(), source='Digital_Input')
        self.channels_led = dict(ao_top_led=AOChannel(name=self.settings.child('ao_leds', 'ao_top_led').value(),
                                                      source='Analog_Input', analog_type='Voltage',
                                                      value_min=-10., value_max=10., termination='Diff', ),
                                 ao_left_led=AOChannel(name=self.settings.child('ao_leds', 'ao_left_led').value(),
                                                       source='Analog_Input', analog_type='Voltage',
                                                       value_min=-10., value_max=10., termination='Diff', ),
                                 ao_right_led=AOChannel(name=self.settings.child('ao_leds', 'ao_right_led').value(),
                                                        source='Analog_Input', analog_type='Voltage',
                                                        value_min=-10., value_max=10., termination='Diff', ),
                                 ao_bottom_led=AOChannel(name=self.settings.child('ao_leds', 'ao_bottom_led').value(),
                                                         source='Analog_Input', analog_type='Voltage',
                                                         value_min=-10., value_max=10., termination='Diff', ),
                                 )

        Nsamples = 1
        self.clock_settings_leds = ClockSettings(frequency=self.settings.child('frequency').value(),
                                                 Nsamples=int(Nsamples))

        self.controller['di'].update_task([self.channel_di])
        self.controller['ao'].update_task([self.channels_led[key] for key in self.channels_led],
                                          self.clock_settings_ai)


    def setupUI(self):
        self.parent.setLayout(QtWidgets.QVBoxLayout())
        self.settings_tree = ParameterTree()
        self.settings_tree.setMinimumWidth(300)
        self.settings = Parameter.create(name='Settings', type='group', children=self.params)
        self.settings_tree.setParameters(self.settings, showTop=False)
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)
        self.parent.layout().addWidget(self.settings_tree)

    def parameter_tree_changed(self, param, changes):
        """

        """
        for param, change, data in changes:
            path = self.settings.childPath(param)
            if change == 'childAdded':
                pass

            elif change == 'value':
                pass

            elif change == 'parent':
                pass


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
            leds_value[key] = self.sliders[key].value() + offset if self.leds[key].get_state() else 0.

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

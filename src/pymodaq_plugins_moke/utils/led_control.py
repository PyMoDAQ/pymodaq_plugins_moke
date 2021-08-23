import sys
from PyQt5 import QtWidgets, QtCore
from pymodaq.resources.QtDesigner_Ressources import QtDesigner_ressources_rc
from pymodaq.daq_utils.parameter.pymodaq_ptypes import SliderSpinBox, QLED
from collections import OrderedDict


class LEDControl(QtCore.QObject):
    leds_value = QtCore.pyqtSignal(dict)

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
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
    widget = QtWidgets.QWidget()
    win.setCentralWidget(widget)
    LEDControl(widget)
    win.setWindowTitle('LEDControls')
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

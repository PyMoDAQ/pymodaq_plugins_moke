import sys
from qtpy import QtWidgets, QtGui, QtCore
from pymodaq.daq_utils.gui_utils import DockArea
from pymodaq.daq_utils.daq_utils import ThreadCommand, set_logger, get_module_name
from pymodaq.dashboard import DashBoard
from pymodaq_plugins_moke.utils.led_control import LedControl
from pathlib import Path
logger = set_logger(get_module_name(__file__))

class MicroMOKE:
    def __init__(self, area, modules_manager):
        self.area = area
        self.modules_manager = modules_manager
        self.toolbar = None

        self.led_control = LedControl(area)
        self.detector = self.modules_manager.get_mod_from_name('Camera', mod='det')
        self.led_actuator = self.modules_manager.get_mod_from_name('LedDriver', mod='act')

        self.setup_UI()
        self.make_connection()

        self.setup_camera()

    def setup_camera(self):
        self.detector.settings.child('detector_settings', 'camera_settings', 'exposure').setValue(100)
        QtWidgets.QApplication.processEvents()
        encoding = self.detector.settings.child('detector_settings', 'camera_settings', 'encoding').opts['limits'][2]
        self.detector.settings.child('detector_settings', 'camera_settings', 'encoding').setValue(encoding)
        QtWidgets.QApplication.processEvents()
        self.detector.settings.child('detector_settings', 'camera_settings', 'image_settings', 'bin_x').setValue(4)
        QtWidgets.QApplication.processEvents()
        self.detector.settings.child('detector_settings', 'camera_settings', 'image_settings', 'bin_y').setValue(4)
        QtWidgets.QApplication.processEvents()

    def setup_UI(self):

        for dock in self.detector.viewer_docks:
            self.detector.dockarea.moveDock(dock, 'right', self.led_control.dock_manual)
        self.area.moveDock(self.led_control.dock_sequence, 'bottom', self.led_control.dock_manual)

        self.create_actions()
        self.create_toolbar()

    def create_actions(self):
        iconquit = QtGui.QIcon()
        iconquit.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/close2.png"), QtGui.QIcon.Normal,
                           QtGui.QIcon.Off)
        self.quit_action = QtWidgets.QAction(iconquit, "Quit program", None)
        self.quit_action.triggered.connect(self.quit_function)

        image_path = str(Path(__file__).parent.joinpath(f'utils/images/sequence.png'))
        iconsequence = QtGui.QIcon()
        iconsequence.addPixmap(QtGui.QPixmap(image_path), QtGui.QIcon.Normal,
                           QtGui.QIcon.Off)
        self.toggle_sequence_action = QtWidgets.QAction(iconsequence, "Toggle between Manual Controler or Sequence "
                                                                      "Control",
                                                        None)
        self.toggle_sequence_action.setCheckable(True)
        self.toggle_sequence_action.triggered.connect(self.set_led_type)

        icon_detector = QtGui.QIcon()
        icon_detector.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/camera.png"), QtGui.QIcon.Normal,
                                QtGui.QIcon.Off)
        self.detector_action = QtWidgets.QAction(icon_detector, "Grab from camera", None)
        self.detector_action.setCheckable(True)
        self.detector_action.triggered.connect(lambda: self.run_detector())

    def create_toolbar(self):
        self.toolbar = QtWidgets.QToolBar()
        self.area.parent().addToolBar(self.toolbar)
        self.toolbar.addAction(self.quit_action)
        self.toolbar.addAction(self.detector_action)
        self.toolbar.addAction(self.toggle_sequence_action)

    def run_detector(self):
        self.detector.grab()

    def quit_function(self):
        self.area.parent().close()

    def make_connection(self):
        self.led_control.led_manual_control.leds_value.connect(self.set_LEDs)
        self.led_control.led_type_signal.connect(self.set_led_type)
        self.led_control.led_sequence_control.sequence_signal.connect(self.set_led_type)

        self.detector.custom_sig.connect(self.info_detector)

    def info_detector(self, status):
        if status.command == 'stopped':
            self.led_actuator.command_stage.emit(ThreadCommand('update_tasks'))
            logger.debug('stopped')

    def set_LEDs(self, led_values):
        self.led_actuator.command_stage.emit(ThreadCommand('set_leds_external', [led_values]))
        if self.toggle_sequence_action.isChecked():
            self.set_led_type()

    def set_led_type(self, led_type=None):
        if not isinstance(led_type, dict):
            if not self.toggle_sequence_action.isChecked():
                led_type = dict(manual=None)
            else:
                sequence = self.led_control.led_sequence_control.sequence
                led_state = dict(top=False, bottom=False, left=False, right=False)
                for seq in sequence:
                    for led in seq:
                        if seq[led] is True:
                            led_state[led] = True
                for led in led_state:
                    self.led_control.led_manual_control.leds[led].set_as(led_state[led])
                led_type = dict(sequence=sequence)


        was_grabing = False
        if self.detector.grab_state:
            was_grabing = True
            self.detector.stop()

        QtWidgets.QApplication.processEvents()
        self.led_actuator.command_stage.emit(ThreadCommand('set_led_type', [led_type]))
        if 'sequence' in led_type:
            do_sub = len(led_type['sequence']) > 1
        else:
            do_sub = False
        self.detector.command_detector.emit(ThreadCommand('activate_substraction', [do_sub]))
        if not do_sub:
            self.detector.ui.viewers[0].setGradient('red', 'grey')
            self.detector.ui.viewers[0].auto_levels_action_sym.setChecked(False)
            self.detector.ui.viewers[0].auto_levels_action_sym.trigger()
        else:

            self.detector.ui.viewers[0].setGradient('red', 'bipolar')
            self.detector.ui.viewers[0].auto_levels_action.setChecked(False)
            self.detector.ui.viewers[0].auto_levels_action_sym.setChecked(True)
            self.detector.ui.viewers[0].auto_levels_action.trigger()
            self.detector.ui.viewers[0].auto_levels_action_sym.trigger()
        QtWidgets.QApplication.processEvents()

        if was_grabing:
            self.detector.grab()

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

    dashboard = DashBoard(area)
    file = Path(get_set_preset_path()).joinpath("microMOKE.xml")
    if file.exists():
        dashboard.set_preset_mode(file)
        #prog.load_scan_module()
        mm_area = DockArea()
        mm_window = QtWidgets.QMainWindow()
        mm_window.setCentralWidget(mm_area)
        micromoke = MicroMOKE(mm_area, dashboard.modules_manager)
        mm_window.show()
        mm_window.setWindowTitle('MicroMOKE')
        QtWidgets.QApplication.processEvents()



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
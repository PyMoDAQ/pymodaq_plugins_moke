import sys
from qtpy import QtWidgets, QtGui, QtCore
from pymodaq.daq_utils import gui_utils as gutils
from pymodaq.daq_utils.daq_utils import ThreadCommand, set_logger, get_module_name
from pymodaq.dashboard import DashBoard
from pymodaq_plugins_moke.utils.led_control import LedControl
from pymodaq_plugins_moke.utils.steps_sequence import StepsSequencer
from pymodaq.daq_utils.messenger import messagebox
from pathlib import Path
logger = set_logger(get_module_name(__file__))


class MicroMOKE(gutils.CustomApp):
    def __init__(self, dockarea, dashboard):
        super().__init__(dockarea, dashboard)
        self.led_control = LedControl(dockarea)
        self.steps_sequencer = StepsSequencer(dockarea)
        self.detector = self.modules_manager.get_mod_from_name('Camera', mod='det')
        self.led_actuator = self.modules_manager.get_mod_from_name('LedDriver', mod='act')

        self.scan_window = QtWidgets.QMainWindow()
        self.dashboard.load_scan_module(win=self.scan_window)
        self.show_scanner(False)

        self.setup_ui()
        self.setup_camera()

    def setup_camera(self):
        try:
            self.detector.settings.child('detector_settings', 'camera_settings', 'exposure').setValue(100)
            QtWidgets.QApplication.processEvents()
            encoding = self.detector.settings.child('detector_settings', 'camera_settings', 'encoding').opts['limits'][2]
            self.detector.settings.child('detector_settings', 'camera_settings', 'encoding').setValue(encoding)
            QtWidgets.QApplication.processEvents()
            self.detector.settings.child('detector_settings', 'camera_settings', 'image_settings', 'bin_x').setValue(4)
            QtWidgets.QApplication.processEvents()
            self.detector.settings.child('detector_settings', 'camera_settings', 'image_settings', 'bin_y').setValue(4)
            QtWidgets.QApplication.processEvents()
        except Exception as e:  # will fail if a Mock camera is used for testing
            pass

    def setup_docks(self):
        for dock in self.detector.viewer_docks:
            self.detector.dockarea.moveDock(dock, 'right', self.led_control.dock_manual)
        self.dockarea.moveDock(self.led_control.dock_sequence, 'bottom', self.led_control.dock_manual)
        self.dockarea.moveDock(self.steps_sequencer.dock, 'right', self.detector.viewer_docks[-1])
        self.show_dashboard(False)

    def setup_actions(self):
        self.add_action('quit', 'Quit', 'close2', "Quit program")
        image_path = str(Path(__file__).parent.joinpath(f'utils/images/sequence.png'))
        self.add_action('toggle_sequence', 'Toggle Sequence', image_path, checkable=True)
        self.add_action('grab', 'Grab', 'camera', "Grab from camera", checkable=True)

        self.toolbar.addSeparator()

        self.add_action('load', 'Load', 'Open', "Load target file (.h5, .png, .jpg) or data from camera",
                        checkable=False)
        self.add_action('save', 'Save', 'SaveAs', "Save current data", checkable=False)
        self.add_action('showdash', 'Show/hide Dashboard', 'read2', "Show Hide Dashboard", checkable=True)
        self.add_action('showscan', 'Show/hide Scanner', 'read2', "Show Hide Scanner Window", checkable=True)


    def connect_things(self):
        self.connect_action('quit', self.quit_function)
        self.connect_action('toggle_sequence', self.set_led_type)
        self.connect_action('grab', lambda: self.run_detector())
        self.connect_action('showdash', self.show_dashboard)
        self.connect_action('showscan', self.show_scanner)

        self.led_control.led_manual_control.leds_value.connect(self.set_LEDs)
        self.led_control.led_type_signal.connect(self.set_led_type)
        self.led_control.led_sequence_control.sequence_signal.connect(self.set_led_type)

        self.detector.custom_sig.connect(self.info_detector)

        self.steps_sequencer.positions_signal.connect(self.dashboard.scan_module.scanner.update_tabular_positions)

    def show_dashboard(self, show=True):
        self.dashboard.mainwindow.setVisible(show)

    def show_scanner(self, show=True):
        self.scan_window.setVisible(show)

    def run_detector(self):
        self.detector.grab()

    def quit_function(self):
        self.dockarea.parent().close()

    def info_detector(self, status):
        if status.command == 'stopped':
            self.led_actuator.command_stage.emit(ThreadCommand('update_tasks'))
            logger.debug('stopped')

    def set_LEDs(self, led_values):
        self.led_actuator.command_stage.emit(ThreadCommand('set_leds_external', [led_values]))
        if self.is_action_checked('toggle_sequence'):
            self.set_led_type()

    def set_led_type(self, led_type=None):
        if not isinstance(led_type, dict):
            if not self.is_action_checked('toggle_sequence'):
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
            self.detector.ui.viewers[0].set_gradient('red', 'grey')
            self.detector.ui.viewers[0].set_action_checked('auto_levels_sym', False)
            self.detector.ui.viewers[0].get_action('auto_levels_sym').trigger()
        else:

            self.detector.ui.viewers[0].set_gradient('red', 'bipolar')
            self.detector.ui.viewers[0].set_action_checked('autolevels', False)
            self.detector.ui.viewers[0].set_action_checked('auto_levels_sym', True)
            self.detector.ui.viewers[0].get_action('autolevels').trigger()
            self.detector.ui.viewers[0].get_action('auto_levels_sym').trigger()
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
    if not file.exists():
        file = Path(get_set_preset_path()).joinpath("MokeMicro_Mock.xml")
    if file.exists():
        dashboard.set_preset_mode(file)
        #prog.load_scan_module()
        mm_area = gutils.DockArea()
        mm_window = QtWidgets.QMainWindow()
        mm_window.setCentralWidget(mm_area)
        micromoke = MicroMOKE(mm_area, dashboard)
        mm_window.show()
        mm_window.setWindowTitle('MicroMOKE')
        QtWidgets.QApplication.processEvents()



    else:
        messagebox(severity='warning', title=f"Impossible to load the DAQ_Scan Module",
                   text=f"The default file specified in the configuration file does not exists!\n"
                   f"{file}\n")

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
import sys
from qtpy import QtWidgets, QtGui, QtCore
from pathlib import Path

from pymodaq.daq_utils.gui_utils.custom_app import CustomApp
from pymodaq.daq_utils.gui_utils.dock import Dock
import pymodaq.daq_utils.gui_utils.layout
from pymodaq.daq_utils import config as config_mod
from pymodaq.daq_utils.daq_utils import ThreadCommand, set_logger, get_module_name

from pymodaq_plugins_moke.utils import LedControl, StepsSequencer, ManualActuation
from pymodaq.daq_utils.messenger import messagebox
from pymodaq.daq_utils.plotting.data_viewers.viewer1D import Viewer1D

from pymodaq_plugins_moke.utils.miscelanous import ConfigMoKe

config = ConfigMoKe()
logger = set_logger(get_module_name(__file__))


class MicroMOKE(CustomApp):
    def __init__(self, dockarea, dashboard):
        super().__init__(dockarea, dashboard)
        self.led_control = LedControl(dockarea)
        self.steps_sequencer = StepsSequencer(dockarea)
        self.manual_actuation = ManualActuation(dockarea,
                                                absolute_values=config('micro', 'actuation', 'absolute_current_values'),
                                                relative_value=config('micro', 'actuation', 'relative_value'))
        self.detector = self.modules_manager.get_mod_from_name('Camera', mod='det')
        self.current_actuator = self.modules_manager.get_mod_from_name('Current', mod='act')
        self.led_actuator = self.modules_manager.get_mod_from_name('LedDriver', mod='act')

        self.scan_window = None

        self.setup_ui()
        self.setup_camera()
        self.setup_scan()

    def setup_scan(self):
        if self.dashboard.scan_module is None:
            self.scan_window = QtWidgets.QMainWindow()
            self.dashboard.load_scan_module(win=self.scan_window)
            self.get_action('show_scan').setEnabled(True)
            self.get_action('do_scan').setEnabled(True)
            self.show_scanner(self.is_action_checked('show_scan'))
            self.connect_action('do_scan', self.dashboard.scan_module.do_scan)
            self.connect_action('do_scan', self.show_hide_live_viewer)
            self.dashboard.scan_module.live_data_1D_signal.connect(self.update_live_viewer)

        self.dashboard.scan_module.scanner.set_scan_type_and_subtypes('Tabular', 'Linear')
        self.dashboard.scan_module.modules_manager.selected_detectors_name = ['Camera']
        self.dashboard.scan_module.modules_manager.selected_actuators_name = ['Current']
        QtWidgets.QApplication.processEvents()

    def update_live_viewer(self, data_all):
        self.scan_live_viewer.show_data(data_all[1], x_axis=data_all[0])

    def show_hide_live_viewer(self, show=True):
        self.scan_live_dock.setVisible(show)

    def setup_camera(self):
        try:
            self.detector.settings.child('detector_settings', 'camera_settings', 'exposure').setValue(100)
            QtWidgets.QApplication.processEvents()
            encoding = self.detector.settings.child('detector_settings', 'camera_settings',
                                                    'encoding').opts['limits'][2]
            self.detector.settings.child('detector_settings', 'camera_settings', 'encoding').setValue(encoding)
            QtWidgets.QApplication.processEvents()
            self.detector.settings.child('detector_settings', 'camera_settings', 'image_settings', 'bin_x').setValue(2)
            QtWidgets.QApplication.processEvents()
            self.detector.settings.child('detector_settings', 'camera_settings', 'image_settings', 'bin_y').setValue(2)
            QtWidgets.QApplication.processEvents()
        except KeyError as e:  # will fail if a Mock camera is used for testing
            pass
        finally:
            self.detector.viewers[0].show_roi(True, False)

    def setup_docks(self):
        for dock in self.detector.viewer_docks:
            self.detector.dockarea.moveDock(dock, 'right', self.led_control.dock_manual)
        self.dockarea.moveDock(self.led_control.dock_sequence, 'bottom', self.led_control.dock_manual)
        self.dockarea.moveDock(self.steps_sequencer.dock, 'bottom', self.led_control.dock_manual)
        self.dockarea.moveDock(self.manual_actuation.dock, 'right', self.led_control.dock_manual)
        self.show_dashboard(False)
        QtWidgets.QApplication.processEvents()
        self.steps_sequencer.dock.resize(QtCore.QSize(350, 100))

        self.scan_live_dock = Dock('Live Scan Plot')
        widget = QtWidgets.QWidget()
        self.scan_live_viewer = Viewer1D(widget)
        self.scan_live_dock.addWidget(widget)
        self.dockarea.addDock(self.scan_live_dock, 'bottom', self.detector.viewer_docks[0])
        self.scan_live_dock.setVisible(False)

    def setup_actions(self):
        self.add_action('quit', 'Quit', 'close2', "Quit program")
        self.add_action('save_layout', 'Save Layout', 'SaveAs', "Save current dock layout", checkable=False)
        self.add_action('load_layout', 'Load Layout', 'Open', "Load dock layout", checkable=False)

        self.toolbar.addSeparator()
        self.add_action('config', 'Show Config', 'gear2', 'Open and change configuration', checkable=False)
        self.toolbar.addSeparator()

        image_path = str(Path(__file__).parent.joinpath(f'utils/images/sequence.png'))
        self.add_action('toggle_sequence', 'Toggle Sequence', image_path, checkable=True)


        self.toolbar.addSeparator()

        self.add_action('load', 'Load', 'Open', "Load target file (.h5, .png, .jpg) or data from camera",
                        checkable=False)
        self.add_action('save', 'Save', 'SaveAs', "Save current data", checkable=False)
        self.add_action('show_dash', 'Show/hide Dashboard', 'read2', "Show Hide Dashboard", checkable=True)
        self.add_action('show_scan', 'Show/hide Scanner', 'read2', "Show Hide Scanner Window", checkable=True)
        self.get_action('show_scan').setEnabled(False)

        self.toolbar.addSeparator()
        self.add_action('snap', 'Snap', 'camera_snap', "Snap from camera", checkable=False)
        self.add_action('grab', 'Grab', 'camera', "Grab from camera", checkable=True)
        self.add_action('do_scan', 'Do Scan', 'run2', checkable=True)
        self.get_action('do_scan').setEnabled(False)

    def show_config(self):
        config_tree = config_mod.TreeFromToml(config=config)
        config_tree.show_dialog()

    def connect_things(self):
        self.connect_action('quit', self.quit_function)
        self.connect_action('toggle_sequence', self.set_led_type)
        self.connect_action('grab', lambda: self.run_detector())
        self.connect_action('snap', lambda: self.run_detector(snap=True))
        self.connect_action('show_dash', self.show_dashboard)
        self.connect_action('show_scan', self.show_scanner)
        self.connect_action('save_layout', self.save_layout)
        self.connect_action('load_layout', self.load_layout)

        self.connect_action('config', self.show_config)

        self.led_control.led_manual_control.leds_value.connect(self.set_LEDs)
        self.led_control.led_type_signal.connect(self.set_led_type)
        self.led_control.led_sequence_control.sequence_signal.connect(self.set_led_type)

        self.detector.custom_sig.connect(self.info_detector)

        self.manual_actuation.actuation_signal.connect(self.current_actuator.move)

        self.steps_sequencer.positions_signal.connect(self.emit_positions)

    def save_layout(self):
        pymodaq.daq_utils.gui_utils.layout.save_layout_state(self.dockarea)

    def load_layout(self):
        pymodaq.daq_utils.gui_utils.layout.load_layout_state(self.dockarea)

    def emit_positions(self, positions):
        self.setup_scan()
        self.dashboard.scan_module.scanner.update_tabular_positions(positions)

    def show_dashboard(self, show=True):
        self.dashboard.mainwindow.setVisible(show)

    def show_scanner(self, show=True):
        if self.scan_window is not None:
            self.scan_window.setVisible(show)

    def run_detector(self, snap=False):
        if snap:
            self.detector.snap()
        else:
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
    from pymodaq.dashboard import DashBoard

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
        mm_area = DockArea()
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

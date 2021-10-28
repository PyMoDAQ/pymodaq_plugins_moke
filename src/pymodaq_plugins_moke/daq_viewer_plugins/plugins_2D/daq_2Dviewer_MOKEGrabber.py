import numpy as np
from qtpy import QtWidgets, QtCore
from easydict import EasyDict as edict
from pymodaq.daq_viewer.utility_classes import DAQ_Viewer_base
from pymodaq.daq_utils.daq_utils import ThreadCommand, DataFromPlugins, Axis, set_logger, get_module_name, zeros_aligned
from pymodaq.daq_viewer.utility_classes import comon_parameters
from pymodaq.daq_utils.parameter.utils import iter_children
import platform
import sys

from pymodaq_plugins_andor.daq_viewer_plugins.plugins_2D.daq_2Dviewer_AndorSCMOS import DAQ_2DViewer_AndorSCMOS
from time import perf_counter

logger = set_logger(get_module_name(__file__))


class DAQ_2DViewer_MOKEGrabber(DAQ_2DViewer_AndorSCMOS):
    """
        Inherited class from Andor SCMOS camera

    """
    hardware_averaging = True  # will use the accumulate acquisition mode if averaging is neccessary
    live_mode_available = True
    params = DAQ_2DViewer_AndorSCMOS.params + \
        [{'title': 'Do substraction:', 'name': 'do_sub', 'type': 'bool', 'value': False}]


    def __init__(self, parent=None, params_state=None):

        super().__init__(parent, params_state)  # initialize base class with commom attributes and methods

        self.buffers = []
        self.buffers_pointer = []
        self._Nbuffers = None
        self._reset_buffers_cmd = False
        self.refresh_time_fr = 200

        self.current_buffer = -1
        self.n_grabed_data = None
        self.n_grabed_frame_rate = None
        self.start_time = None
        self.live = False
        self.wait_time = 0

        self.x_axis = None
        self.y_axis = None
        self.camera_controller = None
        self.data = None
        self.SIZEX, self.SIZEY = (None, None)
        self.camera_done = False
        self.acquirred_image = None
        self.callback_thread = None
        self.Naverage = None
        self.data_shape = None  # 'Data2D' if sizey != 1 else 'Data1D'

        self.temperature_timer = QtCore.QTimer()
        self.temperature_timer.timeout.connect(self.update_temperature)

    def commit_settings(self, param):

        super().commit_settings(param)

    def emit_data(self, buffer_pointer):
        """
            Fonction used to emit data obtained by callback.

            See Also
            --------
            daq_utils.ThreadCommand
        """
        try:

            Naverage_sub = 2 * self.Naverage if self.settings.child('do_sub').value() else self.Naverage

            buff_temp = buffer_pointer[0]
            self.current_buffer += 1
            self.n_grabed_data += 1
            self.n_grabed_frame_rate += 1
            #print(f'ind_grabemit:{self.n_grabed_data}')
            self.current_buffer = self.current_buffer % self._Nbuffers
            #print(f'ind_current_buffer:{self.current_buffer}')

            if self.buffers[self.current_buffer].ctypes.data != buff_temp:
                # buff_val = [self.buffers[ind].ctypes.data for ind in range(len(self.buffers))].index(buff_temp)
                # print(f'Buffer index should be {self.current_buffer} but is in fact {buff_val}')
                self.stop()
                QtWidgets.QApplication.processEvents()

                self.emit_status(ThreadCommand('Update_Status',
                                               ['Returned buffer not equal to expected buffer,'
                                                ' restarting acquisition and'
                                                ' freeing buffers', 'log']))
                logger.warning('Returned buffer not equal to expected buffer, restarting acquisition and'
                               ' freeing buffers')
                self._reset_buffers_cmd = True
                self.grab_data(self.Naverage, live=self.live, wait_time=self.wait_time)
                return

            cam_name = self.settings.child('camera_settings', 'camera_model').value()
            Nx = self.settings.child('camera_settings', 'image_settings', 'im_width').value()
            Ny = self.settings.child('camera_settings', 'image_settings', 'im_height').value()
            data = self.camera_controller.get_image_fom_buffer(Nx, Ny, self.buffers[self.current_buffer]).T

            if (self.n_grabed_data-1) % Naverage_sub == 0 and self.live:
                self.data = 1 / self.Naverage * data
                logger.debug(f'Init data for live')
            else:
                if self.settings.child('do_sub').value():
                    if self.ind_sub % 2 == 0:
                        logger.debug(f'Adding data')
                        self.data += 1 / self.Naverage * data
                    else:
                        self.data -= 1 / self.Naverage * data
                        logger.debug(f'Substracting data')
                else:
                    logger.debug(f'Adding data as normal')
                    self.data += 1 / self.Naverage * data

            logger.debug(f'Naverage_sub: {Naverage_sub}')
            logger.debug(f'n_grabed_data: {self.n_grabed_data}')
            logger.debug(f'ind_sub: {self.ind_sub}')
            logger.debug(f'live: {self.live}')
            self.ind_sub += 1

            if not self.live:
                if self.n_grabed_data > Naverage_sub:
                    self.stop()
                else:
                    #self.data += 1 / self.Naverage * data
                    if self.n_grabed_data == Naverage_sub:
                        logger.debug(f'emit snap')
                        self.data_grabed_signal.emit([
                            DataFromPlugins(name=cam_name, data=[self.data], dim=self.data_shape)])
                        self.stop()
                    # elif self.n_grabed_data < self.Naverage:
                    #     if self.ind_sub % 2 == 1:
                    #         self.data_grabed_signal_temp.emit([
                    #             DataFromPlugins(name=cam_name, data=[self.data * self.Naverage / self.n_grabed_data],
                    #                             dim=self.data_shape)])
            else:  # in live mode
                if perf_counter() - self.start_time > self.refresh_time_fr / 1000:  # refresh the frame rate every
                    # refresh_time_fr ms
                    self.settings.child('camera_settings',
                                        'frame_rate').setValue(self.n_grabed_frame_rate / (self.refresh_time_fr / 1000))
                    self.start_time = perf_counter()
                    self.n_grabed_frame_rate = 0

                if self.n_grabed_data % Naverage_sub == 0:
                    logger.debug(f'emit grab')
                    self.data_grabed_signal.emit([
                        DataFromPlugins(name=cam_name, data=[self.data], dim=self.data_shape)])
                # else:
                #     if self.ind_sub % 2 == 1:
                #         if self.n_grabed_data % self.Naverage != 0:
                #             n_grabed = self.n_grabed_data % self.Naverage
                #         else:
                #             n_grabed = self.Naverage
                #         self.data_grabed_signal_temp.emit([
                #             DataFromPlugins(name=cam_name,
                #                             data=[self.data * self.Naverage / n_grabed],
                #                             dim=self.data_shape)])

            self.camera_controller.queue_single_buffer(self.buffers[self.current_buffer])

        except Exception as e:
            logger.exception(str(e))

    def activate_substraction(self, do_sub=False):
        self.settings.child('do_sub').setValue(do_sub)

    def grab_data(self, Naverage=1, **kwargs):
        """
        """
        self.ind_sub = 0
        Naverage_sub = 2 * Naverage if self.settings.child('do_sub').value() else Naverage
        super().grab_data(Naverage_sub, **kwargs)
        self.Naverage = Naverage

    def stop(self):
        super().stop()
        QtWidgets.QApplication.processEvents()
        self.emit_status(ThreadCommand('stopped'))


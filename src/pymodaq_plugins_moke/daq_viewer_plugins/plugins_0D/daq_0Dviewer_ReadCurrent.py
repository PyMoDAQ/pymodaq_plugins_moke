import numpy as np
from easydict import EasyDict as edict
from pymodaq_utils.utils import ThreadCommand, getLineInfo
from pymodaq.utils.data import DataFromPlugins
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq_plugins_daqmx.hardware.national_instruments.daqmx import DAQmx, ClockSettings, AIChannel, DAQ_NIDAQ_source
from pymodaq_plugins_moke import config

logger = set_logger(get_module_name(__file__))


device_ai = config('micro', 'current', 'device_ai')
channel_ai = config('micro', 'current', 'channel_ai')
resistor = config('micro', 'current', 'resistor')


class DAQ_0DViewer_ReadCurrent(DAQ_Viewer_base):
    """
    """
    params = comon_parameters+[
        {'title': 'Resistance:', 'name': 'resistance', 'type': 'float', 'value': resistor, 'min': 0., 'suffix': 'Ohm'},
        {'title': 'AI Channel:', 'name': 'ai_channel', 'type': 'list',
         'limits': DAQmx.get_NIDAQ_channels(source_type=DAQ_NIDAQ_source.Analog_Input.name),
         'value': f'{device_ai}/{channel_ai}'},
        ]
    hardware_averaging = False
    live_mode_available = False

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)

        self.channels_ai = None
        self.clock_settings = None
        self.data = None
        self.Nsamples = 2
        self.channels = None
        self.live = False

    def commit_settings(self, param):
        """
        """

        self.update_tasks()

    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: (object) custom object of a PyMoDAQ plugin (Slave case). None if only one detector by controller (Master case)

        Returns
        -------
        self.status (edict): with initialization status: three fields:
            * info (str)
            * controller (object) initialized controller
            *initialized: (bool): False if initialization failed otherwise True
        """

        try:
            self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None,controller=None))
            if self.settings.child(('controller_status')).value() == "Slave":
                if controller is None:
                    raise Exception('no controller has been defined externally while this detector is a slave one')
                else:
                    self.controller = controller
            else:

                self.controller = dict(ai=DAQmx())
                #####################################

            self.update_tasks()


            self.status.info = "Current measurement ready"
            self.status.initialized = True
            self.status.controller = self.controller
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [getLineInfo() + str(e), 'log']))
            self.status.info = getLineInfo() + str(e)
            self.status.initialized = False
            return self.status

    def update_tasks(self):

        self.channels_ai = [AIChannel(name=self.settings.child('ai_channel').value(),
                                      source='Analog_Input', analog_type='Voltage',
                                      value_min=-10., value_max=10., termination='Diff', ),
                            ]

        self.clock_settings_ai = ClockSettings(frequency=1000,
                                            Nsamples=10, repetition=self.live)

        self.controller['ai'].update_task(self.channels_ai, self.clock_settings_ai)



    def close(self):
        """
        Terminate the communication protocol
        """
        pass
        ##

    def grab_data(self, Naverage=1, **kwargs):
        """

        Parameters
        ----------
        Naverage: (int) Number of hardware averaging
        kwargs: (dict) of others optionals arguments
        """
        Naverage = max((2, Naverage))  # at least 2 samples have to be grabed
        self.data = None
        update = False

        if 'live' in kwargs:
            if kwargs['live'] != self.live:
                update = True
            self.live = kwargs['live']

        if Naverage != self.Nsamples:
            self.Nsamples = Naverage
            update = True

        if update:
            self.update_tasks()
        while not self.controller['ai'].isTaskDone():
            self.controller['ai'].task.StopTask()

        data = self.controller['ai'].readAnalog(len(self.channels_ai), self.clock_settings_ai)
        data_tot = np.mean(data) / self.settings.child('resistance').value()

        self.data_grabed_signal.emit([DataFromPlugins(name='Current', data=[np.array([data_tot])],
                                                      dim='Data0D',
                                      labels=['Current'])])

    def stop(self):
        try:
            self.controller['ai'].task.StopTask()
        except:
            pass
        ##############################

        return ''


if __name__ == '__main__':
    main(__file__, init=True)

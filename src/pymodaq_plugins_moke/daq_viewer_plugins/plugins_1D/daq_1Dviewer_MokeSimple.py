import numpy as np
from easydict import EasyDict as edict
from pymodaq.daq_utils.daq_utils import ThreadCommand, getLineInfo, DataFromPlugins, Axis
from pymodaq.daq_viewer.utility_classes import DAQ_Viewer_base, comon_parameters
from pymodaq_plugins_daqmx.hardware.national_instruments import daq_NIDAQmx
from pymodaq_plugins_daqmx.hardware.national_instruments.daqmx import DAQmx, DAQ_analog_types, DAQ_thermocouples,\
    DAQ_termination, Edge, DAQ_NIDAQ_source, \
    ClockSettings, AIChannel, Counter, AIThermoChannel, AOChannel, TriggerSettings, DOChannel, DIChannel



class DAQ_1DViewer_MokeSimple(DAQ_Viewer_base):
    """
    """
    params = comon_parameters+[
        {'title': 'Grab Photodiodes:', 'name': 'diodes', 'type': 'bool', 'value': True},
        {'title': 'Acquire:', 'name': 'acquire', 'type': 'bool', 'value': False},
        {'title': 'Frequency Acq.:', 'name': 'frequency', 'type': 'int', 'value': 10000, 'default': 100000, 'min': 1},
        {'title': 'Ncycles:', 'name': 'Ncycles', 'type': 'int', 'value': 1, 'min': 1},
        {'title': 'Frequency Magnet:', 'name': 'frequency_magnet', 'type': 'float', 'value': 50., 'default': 50.,
         'min': 0., 'suffix': 'Hz'},
        {'title': 'Gain:', 'name': 'gain', 'type': 'float', 'value': 500., 'min': 0.},
        {'title': 'Resistance:', 'name': 'resistance', 'type': 'float', 'value': 1.4, 'min': 0., 'suffix': 'Ohm'},
        {'title': 'Oe/A (solenoid):', 'name': 'solenoid', 'type': 'float', 'value': 97.},
        {'title': 'DO MagField:', 'name': 'do_mag', 'type': 'list',
         'values': DAQmx.get_NIDAQ_channels(source_type='Digital_Output'), 'value': 'Dev1/port1/line0'},
        {'title': 'AI Phot. 1:', 'name': 'ai_phot1', 'type': 'list',
         'values': DAQmx.get_NIDAQ_channels(source_type='Analog_Input'), 'value': 'Dev1/ai0'},
        {'title': 'AI Phot. 2:', 'name': 'ai_phot2', 'type': 'list',
         'values': DAQmx.get_NIDAQ_channels(source_type='Analog_Input'), 'value': 'Dev1/ai1'},
        {'title': 'AI Ampli.:', 'name': 'ai_ampli', 'type': 'list',
         'values': DAQmx.get_NIDAQ_channels(source_type='Analog_Input'), 'value': 'Dev1/ai2'},
        {'title': 'AI HField:', 'name': 'ai_hfield', 'type': 'list',
         'values': DAQmx.get_NIDAQ_channels(source_type='Analog_Input'), 'value': 'Dev1/ai3'},
        ]

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
        self.x_axis = None
        self.channel_do = None
        self.channels_phot = None
        self.channels_ai = None
        self.clock_settings = None

    def commit_settings(self, param):
        """
        """
        ## TODO for your custom plugin
        if param.name() == 'diodes':
            if param.value():
                self.settings.child('acquire').setValue(False)
            else:
                self.settings.child('acquire').setValue(True)
        elif param.name() == 'acquire':
            if param.value():
                self.settings.child('diodes').setValue(False)
            else:
                self.settings.child('diodes').setValue(True)

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
                ## TODO for your custom plugin
                self.controller = dict(do=DAQmx(), phot_only=DAQmx(), ai=DAQmx())
                #####################################

            self.update_tasks()


            self.status.info = "Whatever info you want to log"
            self.status.initialized = True
            self.status.controller = self.controller
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [getLineInfo() + str(e), 'log']))
            self.status.info = getLineInfo() + str(e)
            self.status.initialized = False
            return self.status

    def update_tasks(self):

        self.channel_do = DOChannel(name=self.settings.child('do_mag').value(), source='Digital_Output')
        self.channels_phot = [AIChannel(name=self.settings.child('ai_phot1').value(),
                                        source='Analog_Input', analog_type='Voltage',
                                        value_min=-2., value_max=2., termination='RSE', ),
                              AIChannel(name=self.settings.child('ai_phot2').value(),
                                        source='Analog_Input', analog_type='Voltage',
                                        value_min=-2., value_max=2., termination='RSE', ),
                              ]
        self.channels_ai = [AIChannel(name=self.settings.child('ai_ampli').value(),
                                      source='Analog_Input', analog_type='Voltage',
                                      value_min=-10., value_max=10., termination='RSE', ),
                            AIChannel(name=self.settings.child('ai_hfield').value(),
                                      source='Analog_Input', analog_type='Voltage',
                                      value_min=-10., value_max=10., termination='RSE', ),
                            AIChannel(name=self.settings.child('ai_phot1').value(),
                                      source='Analog_Input', analog_type='Voltage',
                                      value_min=-10., value_max=10., termination='RSE', ),
                            ]


        Nsamples = 1 / self.settings.child('frequency_magnet').value() * self.settings.child('frequency').value() \
            * (self.settings.child('Ncycles').value() + 4)

        self.clock_settings_ai = ClockSettings(frequency=self.settings.child('frequency').value(),
                                            Nsamples=int(Nsamples))
        self.clock_settings_phot = ClockSettings(frequency=100, Nsamples=10)

        self.controller['do'].update_task([self.channel_do])
        self.controller['ai'].update_task(self.channels_ai, self.clock_settings_ai)
        self.controller['phot_only'].update_task(self.channels_phot, self.clock_settings_phot)


    def close(self):
        """
        Terminate the communication protocol
        """
        ## TODO for your custom plugin
        self.controller.your_method_to_terminate_the_communication()
        ##

    def grab_data(self, Naverage=1, **kwargs):
        """

        Parameters
        ----------
        Naverage: (int) Number of hardware averaging
        kwargs: (dict) of others optionals arguments
        """

        if self.settings.child('diodes').value():
            while not self.controller['phot_only'].isTaskDone():
                self.controller['phot_only'].task.StopTask()
            if self.controller['phot_only'].c_callback is None:
                    self.controller['phot_only'].register_callback(self.emit_data)
            self.controller['phot_only'].task.StartTask()

        elif self.settings.child('acquire').value():
            while not self.controller['ai'].isTaskDone():
                self.controller['ai'].task.StopTask()
            if self.controller['ai'].c_callback is None:
                    self.controller['ai'].register_callback(self.emit_data)
            self.controller['ai'].task.StartTask()
            self.controller['do'].writeDigital(1, np.array([1], dtype=np.uint8), autostart=True)

    def emit_data(self, taskhandle, status, callbackdata):
        if self.settings.child('acquire').value():
            self.controller['do'].writeDigital(1, np.array([0], dtype=np.uint8), autostart=True)
            channels = self.channels_ai
            data = self.controller['ai'].readAnalog(len(channels), self.clock_settings_ai)
            N = self.clock_settings_ai.Nsamples
            self.controller['ai'].task.StopTask()
        elif self.settings.child('diodes').value():
            channels = self.channels_phot
            data = self.controller['phot_only'].readAnalog(len(channels), self.clock_settings_phot)
            N = self.clock_settings_phot.Nsamples
            self.controller['phot_only'].task.StopTask()

        channels_name = [ch.name for ch in channels]
        data_tot = []

        if self.settings.child('diodes').value():
            for ind in range(len(channels)):
                data_tot.append(np.array([np.mean(data[ind*N:(ind+1)*N])]))
            self.data_grabed_signal.emit([DataFromPlugins(name='NI AI', data=data_tot, dim='Data0D',
                                          labels=channels_name)])
        else:
            for ind in range(len(channels)):
                data_tot.append(data[ind*N:(ind+1)*N])

            ind_start = int(4 / self.settings.child('frequency_magnet').value() *
                            self.settings.child('frequency').value())
            # length = int(self.settings.child('Ncycles').value() / self.settings.child('frequency_magnet').value() * \
            #     self.settings.child('frequency').value())
            # ind_stop = np.min([ind_start+length+1, len(data_tot[0])])
            Bfield = data_tot[0][ind_start:] / self.settings.child('resistance').value() * \
                self.settings.child('solenoid').value()
            rotation = data_tot[1][ind_start:]
            diode = data_tot[2][ind_start:]
            rotation *= 180 / np.pi / (self.settings.child('gain').value() * 4 * diode)

            self.data_grabed_signal.emit([DataFromPlugins(name='NI AI', data=[Bfield, rotation], dim='Data1D',
                                          labels=['Bfield', 'Rotation'],
                                          x_axis=Axis(data=np.linspace(0, N / self.clock_settings_ai.frequency, N),
                                          label='Time', units='s'))])


        return 0  #mandatory for the PyDAQmx callback



    def stop(self):
        try:
            self.controller['do'].writeDigital(1, np.array([0], dtype=np.uint8), autostart=True)
        except:
            pass
        try:
            self.controller['ai'].task.StopTask()
        except:
            pass
        try:
            self.controller['do'].task.StopTask()
        except:
            pass
        try:
            self.controller['phot_only'].task.StopTask()
        except:
            pass
        #self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))
        ##############################

        return ''

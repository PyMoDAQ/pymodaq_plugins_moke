from pymodaq.daq_move.utility_classes import DAQ_Move_base  # base class
from pymodaq.daq_move.utility_classes import comon_parameters  # common set of parameters for all actuators
from pymodaq.daq_utils.daq_utils import ThreadCommand, getLineInfo  # object used to send info back to the main thread
from easydict import EasyDict as edict  # type of dict
import numpy as np
from pymodaq_plugins_daqmx.hardware.national_instruments.daqmx import DAQmx, DAQ_analog_types, DAQ_thermocouples,\
    DAQ_termination, Edge, DAQ_NIDAQ_source, \
    ClockSettings, AIChannel, Counter, AIThermoChannel, AOChannel, TriggerSettings, DOChannel, DIChannel


class DAQ_Move_LedDC4104(DAQ_Move_base):
    """
        Wrapper object to access the Mock fonctionnalities, similar wrapper for all controllers.

        =============== ==============
        **Attributes**    **Type**
        *params*          dictionnary
        =============== ==============
    """
    _controller_units = 'Volts'
    is_multiaxes = True  # set to True if this plugin is controlled for a multiaxis controller (with a unique communication link)
    stage_names = ['offset', 'top', 'left', 'right', 'bottom']  # "list of strings of the multiaxes
    channels = ['top_led', 'left_led', 'right_led', 'bottom_led']
    params = [
                 {'title': 'Top LED:', 'name': 'top_led', 'type': 'group', 'children': [
                     {'title': 'Name:', 'name': 'top_led_ao', 'type': 'list',
                      'values': DAQmx.get_NIDAQ_channels(source_type='Analog_Output'), 'value': 'cDAQ1Mod3/ao2'},
                     {'title': 'Value:', 'name': 'top_led_val', 'type': 'float', 'value': 0, 'min': 0, 'max': 3.5},
                     {'title': 'Activated?:', 'name': 'top_led_act', 'type': 'led_push', 'value': False}
                 ]},
                 {'title': 'Left LED:', 'name': 'left_led', 'type': 'group', 'children': [
                     {'title': 'Name:', 'name': 'left_led_ao', 'type': 'list',
                      'values': DAQmx.get_NIDAQ_channels(source_type='Analog_Output'), 'value': 'cDAQ1Mod3/ao3'},
                     {'title': 'Value:', 'name': 'left_led_val', 'type': 'float', 'value': 0, 'min': 0, 'max': 3.5},
                     {'title': 'Activated?:', 'name': 'left_led_act', 'type': 'led_push', 'value': False}
                 ]},
                 {'title': 'Right LED:', 'name': 'right_led', 'type': 'group', 'children': [
                     {'title': 'Name:', 'name': 'right_led_ao', 'type': 'list',
                      'values': DAQmx.get_NIDAQ_channels(source_type='Analog_Output'), 'value': 'cDAQ1Mod3/ao1'},
                     {'title': 'Value:', 'name': 'right_led_val', 'type': 'float', 'value': 0, 'min': 0, 'max': 3.5},
                     {'title': 'Activated?:', 'name': 'right_led_act', 'type': 'led_push', 'value': False}
                 ]},
                 {'title': 'Bottom LED:', 'name': 'bottom_led', 'type': 'group', 'children': [
                     {'title': 'Name:', 'name': 'bottom_led_ao', 'type': 'list',
                      'values': DAQmx.get_NIDAQ_channels(source_type='Analog_Output'), 'value': 'cDAQ1Mod3/ao0'},
                     {'title': 'Value:', 'name': 'bottom_led_val', 'type': 'float', 'value': 0, 'min': 0, 'max': 3.5},
                     {'title': 'Activated?:', 'name': 'bottom_led_act', 'type': 'led_push', 'value': False}
                 ]},
                 {'title': 'Offset:', 'name': 'offset', 'type': 'slide', 'subtype': 'lin', 'value': 0.0,
                  'limits': [0, 3.5]},
                 {'title': 'Activate All:', 'name': 'activate_all', 'type': 'led_push', 'value': False}]\
             + \
             [{'title': 'MultiAxes:', 'name': 'multiaxes', 'type': 'group','visible':is_multiaxes, 'children':[
                        {'title': 'is Multiaxes:', 'name': 'ismultiaxes', 'type': 'bool', 'value': is_multiaxes, 'default': False},
                        {'title': 'Status:', 'name': 'multi_status', 'type': 'list', 'value': 'Master', 'values': ['Master', 'Slave']},
                        {'title': 'Axis:', 'name': 'axis', 'type': 'list',  'values':stage_names},]}]\
             + comon_parameters

    def __init__(self, parent=None, params_state=None):
        """
            Initialize the the class

            ============== ================================================ ==========================================================================================
            **Parameters**  **Type**                                         **Description**

            *parent*        Caller object of this plugin                    see DAQ_Move_main.DAQ_Move_stage
            *params_state*  list of dicts                                   saved state of the plugins parameters list
            ============== ================================================ ==========================================================================================

        """

        super().__init__(parent, params_state)
        self.led_values = dict(zip(self.channels, [0. for chan in self.channels]))

    def check_position(self):
        """Get the current position from the hardware with scaling conversion.

        Returns
        -------
        float: The position obtained after scaling conversion.
        """

        pos = self.target_position
        ##

        pos = self.get_position_with_scaling(pos)
        self.emit_status(ThreadCommand('check_position',[pos]))
        return pos


    def close(self):
        """
        Terminate the communication protocol
        """
        pass
        ##

    def commit_settings(self, param):
        """
            | Activate any parameter changes on the PI_GCS2 hardware.
            |
            | Called after a param_tree_changed signal from DAQ_Move_main.

        """

        if param.name() == "activate_all":
            for channel in self.channels:
                self.settings.child(channel, f'{channel}_act').setValue(param.value())

        self.check_led_and_update()

    def check_led_and_update(self):
        led_values = self.get_led_values()
        for key in led_values:
            if led_values[key] != self.led_values[key]:
                self.led_values = led_values
                self.update_leds(led_values)
                break

    def update_leds(self, led_values):

        self.controller['ao'].writeAnalog(1, 4, np.array([led_values[channel] for channel in led_values],
                                                       dtype=np.float), autostart=True)

    def get_led_values(self):
        offset = self.settings.child('offset').value()
        leds_value = dict([])
        for channel in self.channels:
            val = self.settings.child(channel, f'{channel}_val').value()
            activated = self.settings.child(channel, f'{channel}_act').value()
            leds_value[channel] = val + offset if activated else 0.

        return leds_value

    def ini_stage(self, controller=None):
        """Actuator communication initialization

        Parameters
        ----------
        controller: (object) custom object of a PyMoDAQ plugin (Slave case). None if only one actuator by controller (Master case)

        Returns
        -------
        self.status (edict): with initialization status: three fields:
            * info (str)
            * controller (object) initialized controller
            *initialized: (bool): False if initialization failed otherwise True
        """


        try:
            # initialize the stage and its controller status
            # controller is an object that may be passed to other instances of DAQ_Move_Mock in case
            # of one controller controlling multiactuators (or detector)

            self.status.update(edict(info="", controller=None, initialized=False))

            # check whether this stage is controlled by a multiaxe controller (to be defined for each plugin)
            # if multiaxes then init the controller here if Master state otherwise use external controller
            if self.settings.child('multiaxes', 'ismultiaxes').value() and self.settings.child('multiaxes',
                                   'multi_status').value() == "Slave":
                if controller is None:
                    raise Exception('no controller has been defined externally while this axe is a slave one')
                else:
                    self.controller = controller
            else:  # Master stage

                self.controller = dict(ao=DAQmx())

            self.update_tasks()

            self.emit_status(ThreadCommand('set_allowed_values', dict(decimals=0, minimum=0, maximum=3.5, step=0.1)))

            self.status.info = "Whatever info you want to log"
            self.status.controller = self.controller
            self.status.initialized = True
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [getLineInfo() + str(e), 'log']))
            self.status.info = getLineInfo() + str(e)
            self.status.initialized = False
            return self.status

    def update_tasks(self):

        self.channels_led = [AOChannel(name=self.settings.child(channel, f'{channel}_ao').value(),
                                       source='Analog_Output', analog_type='Voltage',
                                       value_min=-10., value_max=10.,)
                             for channel in self.channels]


        Nsamples = 1

        self.clock_settings = ClockSettings(frequency=1000,
                                            Nsamples=int(Nsamples))

        self.controller['ao'].update_task(self.channels_led, self.clock_settings)


    def move_Abs(self, position):
        """ Move the actuator to the absolute target defined by position

        Parameters
        ----------
        position: (flaot) value of the absolute target positioning
        """

        position = self.check_bound(position)  #if user checked bounds, the defined bounds are applied here
        position = self.set_position_with_scaling(position)  # apply scaling if the user specified one

        axis = self.settings.child('multiaxes', 'axis').value()
        if axis!= 'offset':
            self.settings.child(axis, f'{axis}_val').setValue(position)
        else:
            self.settings.child(axis).setValue(position)
        self.check_led_and_update()



        ##############################



        self.target_position = position
        self.poll_moving()  #start a loop to poll the current actuator value and compare it with target position

    def move_Rel(self, position):
        """ Move the actuator to the relative target actuator value defined by position

        Parameters
        ----------
        position: (flaot) value of the relative target positioning
        """
        position = self.check_bound(self.current_position+position)-self.current_position
        self.target_position = position + self.current_position

        axis = self.settings.child('multiaxes', 'axis').value()
        if axis != 'offset':
            self.settings.child(axis, f'{axis}_val').setValue(position)
        else:
            self.settings.child(axis).setValue(position)
        self.check_led_and_update()
        self.emit_status(ThreadCommand('Update_Status',['Some info you want to log']))
        ##############################

        self.poll_moving()

    def move_Home(self):
        """
          Send the update status thread command.
            See Also
            --------
            daq_utils.ThreadCommand
        """

        pass
        self.emit_status(ThreadCommand('Update_Status', ['No possible Homing']))
        ##############################


    def stop_motion(self):
      """
        Call the specific move_done function (depending on the hardware).

        See Also
        --------
        move_done
      """

      self.move_done() #to let the interface know the actuator stopped
      ##############################


def main():
    import sys
    from PyQt5 import QtWidgets
    from pymodaq.daq_move.daq_move_main import DAQ_Move
    from pathlib import Path
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    prog = DAQ_Move(Form, title="test",)
    Form.show()
    prog.actuator = Path(__file__).stem[9:]
    prog.init()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

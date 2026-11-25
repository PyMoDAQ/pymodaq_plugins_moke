"""Common code of the simulated actuators of the MOKE bench (see :mod:`.simulated_bench`)"""
import time
from typing import Dict, Tuple

from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, DataActuatorType
from pymodaq.control_modules.daq_move_ui.utils import UiType
from pymodaq.utils.data import DataActuator
from pymodaq_gui.parameter import Parameter
from pymodaq_utils.utils import ThreadCommand

from pymodaq_plugins_moke.hardware.simulated_bench import MokeBench


class SimulatedBenchMove(DAQ_Move_base):
    """Base of the simulated actuators: one instrument of the shared simulated bench.

    The first module initialised (master) creates the bench, the others (slaves, same controller ID) receive it.
    A subclass sets ``_bench_attribute`` (the attribute of the bench the actuator drives) and may list in
    ``_bench_parameters`` the settings it forwards to the bench: ``{setting name: (group, attribute, factor)}``.
    """
    is_multiaxes = False
    data_actuator_type = DataActuatorType.DataActuator
    ui_type = UiType.NONE
    has_encoder = True

    _bench_attribute: str = ''
    _home_value: float = 0.
    _bench_parameters: Dict[str, Tuple[str, str, float]] = {}

    def ini_attributes(self):
        self.controller: MokeBench = None

    def ini_stage(self, controller=None):
        if self.is_master:
            self.controller = MokeBench()
        else:
            self.controller = controller
        for name in self._bench_parameters:
            self._forward(self.settings.child(name))
        return f'Simulated {self._axis_names[0]} actuator of the MOKE bench, no hardware', True

    def close(self):
        if self.is_master and self.controller is not None:
            self.controller.close()

    # to be overridden when the instrument has a response time
    def _read(self) -> float:
        return getattr(self.controller, self._bench_attribute)

    def _write(self, value: float):
        setattr(self.controller, self._bench_attribute, value)

    def get_actuator_value(self) -> DataActuator:
        pos = DataActuator(data=self._read(), units=self.axis_unit)
        return self.get_position_with_scaling(pos)

    def move_abs(self, value: DataActuator):
        value = self.check_bound(value)
        self.target_value = value
        value = self.set_position_with_scaling(value)
        self._write(value.value(self.axis_unit))

    def move_rel(self, value: DataActuator):
        value = self.check_bound(self.current_value + value) - self.current_value
        self.target_value = value + self.current_value
        value = self.set_position_relative_with_scaling(value)
        self._write(self._read() + value.value(self.axis_unit))

    def move_home(self):
        self._write(self._home_value)
        deadline = time.monotonic() + 5.
        while abs(self._read() - self._home_value) > self.settings['epsilon'] and time.monotonic() < deadline:
            time.sleep(0.01)
        self.emit_status(ThreadCommand('Update_Status', [f'{self._axis_names[0]} at home']))
        self.move_done()

    def stop_motion(self):
        self._write(self._read())
        self.move_done()

    def _forward(self, param: Parameter):
        group, attribute, factor = self._bench_parameters[param.name()]
        self.controller.set_parameter(group, attribute, param.value() * factor)

    def commit_settings(self, param: Parameter):
        if param.name() in self._bench_parameters:
            self._forward(param)

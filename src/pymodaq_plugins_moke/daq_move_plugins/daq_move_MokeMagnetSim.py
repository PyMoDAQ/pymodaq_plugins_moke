from pymodaq.control_modules.move_utility_classes import comon_parameters_fun, main

from pymodaq_plugins_moke.hardware.simulated_move import SimulatedBenchMove


class DAQ_Move_MokeMagnetSim(SimulatedBenchMove):
    """Simulated electromagnet of the MOKE bench: the axis is the applied field, in mT.

    The field follows its target with a first order response (time constant ``tau``) and drives the magnetisation of
    the simulated sample, which gives the hysteresis. The direction of the field in the lab frame is set by two
    angles: 0 deg from the sample normal is the polar geometry, 90 deg is in plane (longitudinal geometry when the
    azimuth is 0, in the plane of incidence).

    Compatible devices: none, this is a simulation shared with the other ``MokeXxxSim`` plugins through the
    controller (master/slave, same controller ID). Nothing was tested on a real instrument.
    Tested with PyMoDAQ 5.3.13 on Linux. No driver to install.
    """
    _axis_names = ['field']
    _controller_units = 'mT'
    _epsilons = [0.5]
    _bench_attribute = 'field'
    _bench_parameters = {
        'tau': ('bench', 'field_tau', 1e-3),
        'field_polar': ('bench', 'field_polar', 1.),
        'field_azimuth': ('bench', 'field_azimuth', 1.),
    }
    params = [
        {'title': 'Response time (ms):', 'name': 'tau', 'type': 'float', 'value': 50., 'min': 0.,
         'tip': 'First order response of the field to its target'},
        {'title': 'Field direction from the normal (deg):', 'name': 'field_polar', 'type': 'float', 'value': 0.,
         'tip': '0: perpendicular to the sample (polar geometry), 90: in plane'},
        {'title': 'Field azimuth (deg):', 'name': 'field_azimuth', 'type': 'float', 'value': 0.,
         'tip': 'Azimuth in the lab frame, 0: in the plane of incidence'},
    ] + comon_parameters_fun(is_multiaxes=False, axis_names=_axis_names, epsilon=_epsilons)

    def _read(self) -> float:
        return self.controller.get_field()

    def _write(self, value: float):
        self.controller.set_field_target(value)


if __name__ == '__main__':
    main(__file__)

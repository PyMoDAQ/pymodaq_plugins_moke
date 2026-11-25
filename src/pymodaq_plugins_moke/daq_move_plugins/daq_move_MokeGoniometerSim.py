from pymodaq.control_modules.move_utility_classes import comon_parameters_fun, main

from pymodaq_plugins_moke.hardware.simulated_move import SimulatedBenchMove


class DAQ_Move_MokeGoniometerSim(SimulatedBenchMove):
    """Simulated goniometer: angle of incidence of the probe beam on the sample, in degrees (0 is normal incidence).

    The longitudinal Kerr signal grows as the sine of this angle, the polar one is not changed in this model.

    Compatible devices: none, this is a simulation shared with the other ``MokeXxxSim`` plugins through the
    controller (master/slave, same controller ID). Nothing was tested on a real instrument.
    Tested with PyMoDAQ 5.3.13 on Linux. No driver to install.
    """
    _axis_names = ['incidence']
    _controller_units = 'deg'
    _epsilons = [0.01]
    _bench_attribute = 'incidence'
    _home_value = 45.
    params = comon_parameters_fun(is_multiaxes=False, axis_names=_axis_names, epsilon=_epsilons)


if __name__ == '__main__':
    main(__file__)

from pymodaq.control_modules.move_utility_classes import comon_parameters_fun, main

from pymodaq_plugins_moke.hardware.simulated_move import SimulatedBenchMove


class DAQ_Move_MokeSampleRotationSim(SimulatedBenchMove):
    """Simulated rotation stage of the sample about its normal (azimuth of the sample), in degrees.

    It rotates the easy axis of the simulated sample with respect to the plane of incidence and to the field, which
    changes the mix of polar and longitudinal contributions and the shape of the loop.

    Compatible devices: none, this is a simulation shared with the other ``MokeXxxSim`` plugins through the
    controller (master/slave, same controller ID). Nothing was tested on a real instrument.
    Tested with PyMoDAQ 5.3.13 on Linux. No driver to install.
    """
    _axis_names = ['azimuth']
    _controller_units = 'deg'
    _epsilons = [0.01]
    _bench_attribute = 'sample_rotation'
    params = comon_parameters_fun(is_multiaxes=False, axis_names=_axis_names, epsilon=_epsilons)


if __name__ == '__main__':
    main(__file__)

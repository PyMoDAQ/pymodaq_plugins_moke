"""Physics of the simulated MOKE bench (no PyMoDAQ module needed): loops, balance, geometry, imperfections."""
import numpy as np
import pytest

from pymodaq_plugins_moke.hardware.simulated_bench import MokeBench, MODELS


class FakeClock:
    def __init__(self):
        self.t = 0.

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def make_bench(model=MODELS[0], imperfections=False, **sample):
    clock = FakeClock()
    bench = MokeBench(clock=clock, seed=3)
    bench.imperfections.enabled = imperfections
    bench.sample.model = model
    for key, value in sample.items():
        setattr(bench.sample, key, value)
    bench._m = bench._easy_axis()
    bench.clock = clock
    return bench


def sweep(bench, fields):
    """Difference signal (V) at each field once the magnet has settled"""
    out = []
    for field in fields:
        bench.set_field_target(field)
        bench.clock.advance(10 * bench.field_tau + 1e-3)
        out.append(bench.read_diodes()['difference'])
    return np.array(out)


FIELDS_UP = np.linspace(-100, 100, 41)
FIELDS = np.concatenate([FIELDS_UP, FIELDS_UP[::-1]])


@pytest.mark.parametrize('model', MODELS)
def test_loop_is_a_hysteresis_with_the_expected_coercive_field(model):
    bench = make_bench(model, hk=40., hc=15.)
    signal = sweep(bench, FIELDS)
    up, down = signal[:41], signal[41:][::-1]
    assert np.sign(up[0]) == -1 and np.sign(up[-1]) == 1  # saturates on both sides
    zero = 20
    assert up[zero] * down[zero] < 0  # opposite remanent states at zero field
    switch_up = FIELDS_UP[np.argmax(up > 0)]
    expected = 40. if model == MODELS[0] else 15.
    assert switch_up == pytest.approx(expected, abs=5.)


def test_balance_is_at_22_5_degrees_and_offset_grows_away_from_it():
    bench = make_bench(kerr_polar=0.)
    bench.waveplate_angle = 22.5
    balanced = bench.read_diodes()
    assert balanced['difference'] == pytest.approx(0., abs=1e-9)
    assert balanced['diode_A'] == pytest.approx(balanced['diode_B'])
    bench.waveplate_angle = 24.5
    assert bench.read_diodes()['difference'] > 1e-3 * balanced['sum']


def test_difference_gives_the_kerr_rotation_at_balance():
    bench = make_bench(model='tanh', kerr_polar=0.5e-3)
    sweep(bench, [100.])
    out = bench.read_diodes()
    assert out['difference'] / (2 * out['sum']) == pytest.approx(0.5e-3, rel=1e-3)


def test_sensitivity_drops_away_from_balance():
    """The slope of the difference with the Kerr rotation is cos(2 delta) of its maximum, delta being the rotation of
    the polarisation away from the balance: 10 deg of waveplate is 20 deg of polarisation, factor sin(130 deg)"""
    def sensitivity(waveplate_angle):
        bench = make_bench(model='tanh', kerr_polar=0.)
        bench.waveplate_angle = waveplate_angle
        base = bench.read_diodes()
        bench.sample.kerr_polar = 1e-3
        bench._m = np.array([0., 0., 1.])
        shifted = bench.read_diodes()
        return (shifted['difference'] - base['difference']) / base['sum']

    assert sensitivity(32.5) / sensitivity(22.5) == pytest.approx(np.sin(np.radians(130)), rel=1e-3)


def test_hidden_waveplate_zero_shifts_the_balance():
    bench = make_bench(kerr_polar=0.)
    bench.optics.waveplate_zero = 3.
    assert abs(bench.read_diodes()['difference']) > 1e-4
    bench.waveplate_angle = 22.5 + 3.
    assert bench.read_diodes()['difference'] == pytest.approx(0., abs=1e-9)


def test_longitudinal_signal_scales_with_the_sine_of_the_incidence():
    amplitudes = {}
    for incidence in (0., 30., 60.):
        bench = make_bench(model='tanh', easy_polar=90., kerr_polar=0., kerr_long=0.4e-3)
        bench.field_polar = 90.
        bench.incidence = incidence
        sweep(bench, [100.])
        amplitudes[incidence] = bench.read_diodes()['difference']
    assert amplitudes[0.] == pytest.approx(0., abs=1e-9)
    assert amplitudes[60.] / amplitudes[30.] == pytest.approx(np.sin(np.radians(60)) / np.sin(np.radians(30)), rel=1e-3)


def test_sample_rotation_changes_the_stoner_wohlfarth_loop():
    """In plane easy axis, field in the plane of incidence: the loop is square when the axis is along the field and
    closes (no coercivity) when the sample is rotated by 90 deg"""
    widths = {}
    for rotation in (0., 90.):
        bench = make_bench(easy_polar=90., kerr_polar=0., kerr_long=0.4e-3, hk=40.)
        bench.field_polar = 90.
        bench.sample_rotation = rotation
        bench._m = bench._easy_axis()
        signal = sweep(bench, FIELDS)
        up, down = signal[:41], signal[41:][::-1]
        widths[rotation] = np.sum(np.abs(up - down)) / np.max(np.abs(signal))
    assert widths[0.] > 10 * max(widths[90.], 1e-3)


def test_field_follows_its_target_with_the_response_time():
    bench = make_bench()
    bench.field_tau = 0.1
    bench.set_field_target(50.)
    bench.clock.advance(0.1)
    assert bench.get_field() == pytest.approx(50. * (1 - np.exp(-1)), rel=1e-6)
    bench.clock.advance(2.)
    assert bench.get_field() == pytest.approx(50., rel=1e-6)


def test_imperfections_only_when_enabled():
    quiet = make_bench(imperfections=False)
    assert quiet.read_diodes()['difference'] == quiet.read_diodes()['difference']  # deterministic
    noisy = make_bench(imperfections=True)
    values = [noisy.read_diodes()['difference'] for _ in range(200)]
    assert 1e-6 < np.std(values) < 1e-3


def test_laser_noise_is_rejected_by_the_balance_but_not_by_the_sum():
    bench = make_bench(imperfections=True, kerr_polar=0.)
    bench.imperfections.shot_noise = False
    bench.imperfections.electronic_noise = False
    bench.imperfections.laser_noise_rms = 0.01
    reads = [bench.read_diodes() for _ in range(300)]
    std_sum = np.std([r['sum'] for r in reads]) / np.mean([r['sum'] for r in reads])
    std_diff = np.std([r['difference'] for r in reads]) / np.mean([r['sum'] for r in reads])
    assert std_sum == pytest.approx(0.01, rel=0.2)
    assert std_diff < 0.01 * std_sum  # perfectly balanced: no laser noise in the difference


def test_unknown_parameter_is_refused():
    with pytest.raises(KeyError):
        MokeBench().set_parameter('sample', 'not_a_parameter', 1)

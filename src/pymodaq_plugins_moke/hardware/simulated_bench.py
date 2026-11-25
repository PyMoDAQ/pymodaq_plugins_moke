"""Simulated MOKE bench with balanced detection (no hardware needed).

The bench is the *controller* shared by the simulated instruments (magnet, half-wave plate, sample rotation,
goniometer, balanced detector): the first plugin initialised is the master and creates it, the others receive it
as slaves.

Physics, in short (all of it approximate, to be reviewed by MOKE experts, see ``DOC`` below):

* Lab frame: ``z`` is the sample normal, ``x`` lies in the plane of incidence, ``y`` is perpendicular to it.
* Magnetisation: unit vector ``m``. ``stoner_wohlfarth`` model: uniaxial anisotropy field ``Hk`` along an easy axis
  fixed in the sample, ``m`` follows the local minimum of the energy and jumps when this minimum disappears (this
  gives the hysteresis). ``tanh`` model: ``m`` stays along the easy axis, its amplitude follows two tanh branches
  (coercive field, width).
* Kerr rotation (rad): ``K_polar * mz + K_long * sin(incidence) * mx`` (``K_*`` are the values at saturation).
  A transverse term changes the reflected intensity (p polarisation only): ``K_trans * sin(incidence) * my``.
* Balanced detection: a half-wave plate at angle ``alpha`` rotates the polarisation by ``2 alpha`` in front of a
  polarising beam splitter. Photodiode A gets ``P sin^2(phi)`` and B gets ``P cos^2(phi)`` with
  ``phi = 2 (alpha - alpha_zero) + theta_K``. The beams are balanced at ``alpha - alpha_zero = 22.5 deg`` where
  ``A - B = P sin(2 theta_K)``; away from it the offset grows and the sensitivity drops as ``cos(2 delta)``.
"""
from dataclasses import dataclass, field, fields
import math
import threading
import time
from typing import Callable, Optional

import numpy as np

DOC = __doc__

ELECTRON_CHARGE = 1.602176634e-19  # C
MT_TO_A_PER_M = 1e-3 / (4e-7 * math.pi)  # B = mu0 H in vacuum: 1 mT <-> 795.77 A/m
MODELS = ['Stoner-Wohlfarth', 'tanh']


def unit_vector(polar_deg: float, azimuth_deg: float) -> np.ndarray:
    """Unit vector from a polar angle (from z) and an azimuth (from x), in degrees"""
    t, p = math.radians(polar_deg), math.radians(azimuth_deg)
    return np.array([math.sin(t) * math.cos(p), math.sin(t) * math.sin(p), math.cos(t)])


@dataclass
class SampleSettings:
    model: str = MODELS[0]
    hk: float = 40.  # mT, anisotropy field (Stoner-Wohlfarth): the switching field is Hk along the easy axis, Hk/2 at 45 deg
    hc: float = 15.  # mT, coercive field (tanh model)
    width: float = 4.  # mT, width of the switching (tanh model)
    easy_polar: float = 0.  # deg, easy axis from the normal (0: perpendicular anisotropy, 90: in plane)
    easy_azimuth: float = 0.  # deg, easy axis azimuth in the sample frame
    kerr_polar: float = 0.5e-3  # rad, polar Kerr rotation at saturation (m = +z)
    kerr_long: float = 0.3e-3  # rad, longitudinal Kerr rotation at saturation and 90 deg incidence (m = +x)
    kerr_trans: float = 1e-3  # relative reflectivity change at saturation (m = +y, p polarisation)
    kerr_s_over_p: float = 1.  # ratio of the Kerr rotations in s and p polarisation (simple model)
    polarization: str = 'p'  # incident polarisation, 'p' or 's'


@dataclass
class OpticsSettings:
    power: float = 1.  # mW, power of the probe beam on the sample
    reflectivity: float = 0.5
    responsivity: float = 0.5  # A/W of the photodiodes
    gain: float = 1e3  # V/A, transimpedance of each diode amplifier
    bandwidth: float = 50.  # Hz, detection bandwidth (sets the shot noise)
    waveplate_zero: float = 0.  # deg, unknown offset of the zero of the half-wave plate (hidden defect)


@dataclass
class ImperfectionSettings:
    enabled: bool = True  # master switch
    shot_noise: bool = True
    electronic_noise: bool = True
    electronic_noise_rms: float = 20e-6  # V on each channel
    laser_noise: bool = True
    laser_noise_rms: float = 1e-3  # relative intensity noise (common to both diodes)
    imbalance: bool = False
    imbalance_percent: float = 2.  # % gain difference between diodes A and B
    faraday: bool = False
    faraday_slope: float = 5e-6  # rad/mT, linear rotation of the optics in the field
    drift: bool = False
    drift_amplitude: float = 0.2e-3  # rad, slow oscillation of the polarisation
    drift_period: float = 60.  # s


class MokeBench:
    """Simulated MOKE bench: magnet, sample, optics and balanced photodetector"""

    def __init__(self, clock: Callable[[], float] = time.monotonic, seed: Optional[int] = None):
        self._lock = threading.RLock()
        self._clock = clock
        self.rng = np.random.default_rng(seed)
        self.sample = SampleSettings()
        self.optics = OpticsSettings()
        self.imperfections = ImperfectionSettings()
        # instruments
        self.field_tau = 0.05  # s, first order response of the magnet
        self.field_polar = 0.  # deg, direction of the field from the sample normal (0: polar geometry, 90: in plane)
        self.field_azimuth = 0.  # deg, in the lab frame (0: in the plane of incidence)
        self.waveplate_angle = 22.5  # deg
        self.sample_rotation = 0.  # deg, rotation of the sample about its normal
        self.incidence = 45.  # deg, angle of incidence
        # state
        self._field = 0.
        self._field_target = 0.
        self._t_field = clock()
        self._t0 = self._t_field
        self._m = unit_vector(self.sample.easy_polar, self.sample.easy_azimuth + self.sample_rotation)
        self._branch = 1.  # tanh model: last sweep direction
        self._h_projected_last = 0.
        self.closed = False

    # ------------------------------------------------------------------ settings
    def set_parameter(self, group: str, name: str, value):
        """Set ``name`` of the settings ``group`` ('sample', 'optics', 'imperfections') or of the bench ('bench')"""
        with self._lock:
            target = self if group == 'bench' else getattr(self, group)
            if not hasattr(target, name):
                raise KeyError(f'{group}.{name} is not a parameter of the simulated bench')
            setattr(target, name, value)

    def get_parameters(self, group: str) -> dict:
        target = getattr(self, group)
        return {f.name: getattr(target, f.name) for f in fields(target)}

    # ------------------------------------------------------------------ magnet
    def set_field_target(self, value: float):
        with self._lock:
            self._advance_field()
            self._field_target = float(value)

    def get_field(self) -> float:
        with self._lock:
            self._advance_field()
            return self._field

    def _advance_field(self):
        """Move the field toward its target (first order response) and let the magnetisation follow"""
        now = self._clock()
        dt = max(now - self._t_field, 0.)
        self._t_field = now
        f0, target = self._field, self._field_target
        if self.field_tau <= 0:
            f1 = target
        else:
            f1 = target + (f0 - target) * math.exp(-dt / self.field_tau)
        if f1 != f0:
            self._follow_field(f0, f1)
        self._field = f1

    # ------------------------------------------------------------------ magnetisation
    def _easy_axis(self) -> np.ndarray:
        return unit_vector(self.sample.easy_polar, self.sample.easy_azimuth + self.sample_rotation)

    def _field_direction(self) -> np.ndarray:
        return unit_vector(self.field_polar, self.field_azimuth)

    def _follow_field(self, f0: float, f1: float):
        s = self.sample
        if s.model == 'tanh':
            self._follow_tanh(f1)
            return
        hk = max(s.hk, 1e-9)
        n_sub = int(min(abs(f1 - f0) / (0.02 * hk), 400)) + 1
        for f in np.linspace(f0, f1, n_sub + 1)[1:]:
            self._m = self._relax(self._m, self._field_direction() * f / hk, self._easy_axis())

    def _relax(self, m: np.ndarray, h: np.ndarray, easy: np.ndarray, max_iter: int = 600) -> np.ndarray:
        """Follow the local minimum of e(m) = -(m.easy)^2 / 2 - h.m on the unit sphere (h in units of Hk)

        A tiny random tilt (a stand-in for thermal fluctuations) lets m leave a stationary point that has become
        unstable, which would otherwise be kept forever when the field is exactly along the easy axis.
        """
        m = m + 1e-4 * self.rng.standard_normal(3)
        m = m / np.linalg.norm(m)
        for _ in range(max_iter):
            grad = -np.dot(m, easy) * easy - h
            grad_t = grad - np.dot(grad, m) * m
            if np.dot(grad_t, grad_t) < 1e-18:
                break
            m = m - 0.4 * grad_t
            m = m / np.linalg.norm(m)
        return m

    def _follow_tanh(self, f1: float):
        s = self.sample
        easy = self._easy_axis()
        h = f1 * float(np.dot(self._field_direction(), easy))  # field component along the easy axis
        if h > self._h_projected_last:
            self._branch = 1.
        elif h < self._h_projected_last:
            self._branch = -1.
        self._h_projected_last = h
        w = max(s.width, 1e-9)
        m_up = math.tanh((h - s.hc) / w)  # ascending branch
        m_down = math.tanh((h + s.hc) / w)  # descending branch
        amplitude = float(np.dot(self._m, easy))
        amplitude = max(amplitude, m_up) if self._branch > 0 else min(amplitude, m_down)
        self._m = easy * amplitude

    def magnetisation(self) -> np.ndarray:
        """Unit vector (tanh model: reduced) of the magnetisation in the lab frame"""
        with self._lock:
            self._advance_field()
            return self._m.copy()

    # ------------------------------------------------------------------ optics and detection
    def kerr_rotation(self, m: Optional[np.ndarray] = None) -> float:
        """Kerr rotation (rad) of the sample for the magnetisation ``m`` and the present geometry"""
        s = self.sample
        if m is None:
            m = self.magnetisation()
        sin_i = math.sin(math.radians(self.incidence))
        rotation = s.kerr_polar * m[2] + s.kerr_long * sin_i * m[0]
        if s.polarization == 's':
            rotation *= s.kerr_s_over_p
        return float(rotation)

    def read_diodes(self, t_int: float = 0.0) -> dict:
        """Voltages (V) of photodiodes A and B, their difference and sum, with the enabled imperfections"""
        with self._lock:
            m = self.magnetisation()
            field = self._field
            theta_k = self.kerr_rotation(m)
            o, s, imp = self.optics, self.sample, self.imperfections
            active = imp.enabled
            rng = self.rng
            sin_i = math.sin(math.radians(self.incidence))

            if active and imp.faraday:
                theta_k += imp.faraday_slope * field
            if active and imp.drift:
                theta_k += imp.drift_amplitude * math.sin(2 * math.pi * (self._clock() - self._t0) / imp.drift_period)

            power = o.power * 1e-3 * o.reflectivity  # W
            if s.polarization == 'p':
                power *= 1 + s.kerr_trans * sin_i * m[1]
            if active and imp.laser_noise:
                power *= 1 + imp.laser_noise_rms * rng.standard_normal()

            alpha = self.waveplate_angle - o.waveplate_zero
            phi = math.radians(2 * alpha) + theta_k
            p_a, p_b = power * math.sin(phi) ** 2, power * math.cos(phi) ** 2

            gain_a = gain_b = o.gain * o.responsivity  # V/W
            if active and imp.imbalance:
                gain_a *= 1 + imp.imbalance_percent / 200.
                gain_b *= 1 - imp.imbalance_percent / 200.
            v_a, v_b = gain_a * p_a, gain_b * p_b

            bandwidth = o.bandwidth if t_int <= 0 else 1. / (2. * t_int)
            if active and imp.shot_noise:
                for name, p in (('a', p_a), ('b', p_b)):
                    sigma_i = math.sqrt(2 * ELECTRON_CHARGE * max(o.responsivity * p, 0.) * bandwidth)
                    if name == 'a':
                        v_a += o.gain * sigma_i * rng.standard_normal()
                    else:
                        v_b += o.gain * sigma_i * rng.standard_normal()
            if active and imp.electronic_noise:
                v_a += imp.electronic_noise_rms * rng.standard_normal()
                v_b += imp.electronic_noise_rms * rng.standard_normal()
            return dict(diode_A=float(v_a), diode_B=float(v_b), difference=float(v_a - v_b), sum=float(v_a + v_b))

    def close(self):
        self.closed = True

"""Draws docs/moke_bench_angles.png / .svg: how the angles of the simulated MOKE bench are defined.

Run ``python docs/make_angles_figure.py`` (needs matplotlib)."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, FancyArrowPatch, Polygon

OUT = Path(__file__).parent
BEAM, FIELD, SAMPLE, POL, AXIS = '#c0392b', '#2471a3', '#444444', '#1e8449', '#7d3c98'


def arrow(ax, p0, p1, color, lw=2., style='-|>', ls='-', ms=14, z=3):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=ms, color=color, lw=lw, ls=ls, zorder=z))


def arc(ax, center, r, a0, a1, color, label=None, label_r=None, fs=11, lw=1.4):
    ax.add_patch(Arc(center, 2 * r, 2 * r, theta1=a0, theta2=a1, color=color, lw=lw, zorder=4))
    if label:
        a = np.radians((a0 + a1) / 2)
        lr = label_r or r * 1.35
        ax.text(center[0] + lr * np.cos(a), center[1] + lr * np.sin(a), label, color=color, fontsize=fs,
                ha='center', va='center', zorder=5)


def polar(r, deg):
    return r * np.cos(np.radians(deg)), r * np.sin(np.radians(deg))


def setup(ax, title, xlim, ylim):
    ax.set_xlim(*xlim), ax.set_ylim(*ylim)
    ax.set_aspect('equal'), ax.axis('off')
    ax.set_title(title, fontsize=12, fontweight='bold', loc='left')


fig, axes = plt.subplots(1, 3, figsize=(17, 6.2), gridspec_kw=dict(width_ratios=[1.15, 1, 1]))

# ---------------------------------------------------------------- A: side view, plane of incidence (x-z)
ax = axes[0]
setup(ax, 'A  Side view, in the plane of incidence (x, z)', (-2.3, 2.6), (-1.75, 2.9))
ax.add_patch(Polygon([(-2, 0), (2.1, 0), (2.1, -0.18), (-2, -0.18)], color='#d5d8dc', zorder=1))
ax.plot([-2, 2.1], [0, 0], color=SAMPLE, lw=2.5, zorder=2)
ax.text(-2.2, -0.42, 'sample surface', color=SAMPLE, fontsize=10)
arrow(ax, (0, 0), (0, 2.5), SAMPLE, lw=1.2, ls='--')
ax.text(0.07, 2.55, 'z  (sample normal)', fontsize=10, color=SAMPLE)
arrow(ax, (0, 0), (2.4, 0), SAMPLE, lw=1.2, ls='--', style='-|>')
ax.text(2.2, -0.34, 'x', fontsize=10, color=SAMPLE)
ti = 32
bx, bz = polar(2.3, 90 + ti)
arrow(ax, (bx, bz), (0, 0), BEAM, lw=2.5)
ex, ez = polar(2.3, 90 - ti)
arrow(ax, (0, 0), (ex, ez), BEAM, lw=2.5, ls=(0, (4, 2)))
ax.text(bx - 0.35, bz + 0.12, 'probe beam\n(polarisation s or p)', color=BEAM, fontsize=10, ha='center')
ax.text(ex + 0.1, ez + 0.1, 'reflected\nbeam', color=BEAM, fontsize=10, ha='center')
arc(ax, (0, 0), 1.05, 90, 90 + ti, BEAM, r'$\theta_i$', 1.3, fs=13)
ax.text(-2.2, -0.85, 'Goniometer:\n' r'$\theta_i$ = angle of incidence', color=BEAM, fontsize=10.5, va='top')
tH = 62
fx, fz = polar(1.95, 90 - tH)
arrow(ax, (0, 0), (fx, fz), FIELD, lw=3.5)
arc(ax, (0, 0), 0.62, 90 - tH, 90, FIELD, r'$\theta_H$', 0.8, fs=13)
ax.text(fx + 0.12, fz - 0.05, 'B\n(field)', color=FIELD, fontsize=11, fontweight='bold')
ax.text(0.2, -0.85, 'Magnet: B (mT) is the actuator value;\n' r'$\theta_H$ = "Field direction from the normal":' '\n0° polar geometry, 90° in plane',
        color=FIELD, fontsize=10, va='top')

# ---------------------------------------------------------------- B: top view (x-y)
ax = axes[1]
setup(ax, 'B  Top view (x, y): sample, easy axis, field', (-2.4, 2.7), (-3.2, 2.5))
ax.add_patch(Polygon([(-2.3, -0.28), (2.5, -0.28), (2.5, 0.28), (-2.3, 0.28)], color='#fdedec', zorder=0))
ax.text(-2.25, 0.4, 'plane of incidence (x)', color=BEAM, fontsize=9.5)
arrow(ax, (-2.2, 0), (-0.05, 0), BEAM, lw=2.2)
ax.text(-2.2, -0.2, 'beam', color=BEAM, fontsize=9.5, va='top')
psi, phi_e, phi_h = 28, 40, -35
rot = np.radians(psi)
R = np.array([[np.cos(rot), -np.sin(rot)], [np.sin(rot), np.cos(rot)]])
sq = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]]) * 0.95
ax.add_patch(Polygon((R @ sq.T).T, closed=True, fc='#eaecee', ec=SAMPLE, lw=2, zorder=1))
ax.text(*(R @ np.array([0.45, -0.7])), 'sample', color=SAMPLE, fontsize=10, rotation=psi, ha='center', va='center')
arrow(ax, (0, 0), (2.4, 0), SAMPLE, lw=1.1, ls='--')
ax.text(2.45, -0.17, 'x', fontsize=10, color=SAMPLE)
arrow(ax, (0, 0), (0, 2.05), SAMPLE, lw=1.1, ls='--')
ax.text(0.07, 2.08, 'y', fontsize=10, color=SAMPLE)
xs = polar(1.85, psi)
arrow(ax, (0, 0), xs, SAMPLE, lw=1.4, ls=(0, (3, 2)), ms=10)
ax.text(xs[0] + 0.08, xs[1] + 0.02, r'$x_s$ (sample)', fontsize=9.5, color=SAMPLE)
arc(ax, (0, 0), 1.25, 0, psi, SAMPLE, r'$\psi$', 1.5, fs=13)
ea = polar(2.15, psi + phi_e)
arrow(ax, (-ea[0] * 0.55, -ea[1] * 0.55), ea, AXIS, lw=2.6, style='<|-|>', ms=14)
ax.text(ea[0] + 0.05, ea[1] + 0.12, 'easy axis', color=AXIS, fontsize=10.5)
arc(ax, (0, 0), 0.8, psi, psi + phi_e, AXIS, r'$\phi_e$', 1.05, fs=13)
fh = polar(2.2, phi_h)
arrow(ax, (0, 0), fh, FIELD, lw=3.5)
arc(ax, (0, 0), 1.6, phi_h, 0, FIELD, r'$\phi_H$', 1.88, fs=13)
ax.text(fh[0] + 0.1, fh[1] - 0.12, 'B (in-plane\ncomponent)', color=FIELD, fontsize=10, ha='left', va='top')
ax.text(-2.35, -1.95,
        r'Sample rotation stage: $\psi$ = azimuth of the sample (from x)' '\n'
        r'Sample setting "Easy axis azimuth": $\phi_e$, measured from $x_s$' '\n'
        r'Magnet setting "Field azimuth": $\phi_H$, from x, in the lab' '\n'
        'The easy axis is at ' r'$\psi + \phi_e$' ' from x in the lab',
        fontsize=9.5, va='top', linespacing=1.5)

# ---------------------------------------------------------------- C: polarisation, half-wave plate, PBS
ax = axes[2]
setup(ax, 'C  Polarisation in front of the polarising beam splitter', (-2.2, 2.6), (-2.5, 2.4))
arrow(ax, (-2.0, 0), (2.1, 0), SAMPLE, lw=1.2)
ax.text(1.55, -0.3, 'port B axis', color=SAMPLE, fontsize=10)
arrow(ax, (0, -0.9), (0, 2.0), SAMPLE, lw=1.2, style='-|>')
ax.text(0.08, 2.05, 'port A axis', color=SAMPLE, fontsize=10)
al = 14
fa = polar(2.0, al)
ax.plot([-fa[0], fa[0]], [-fa[1], fa[1]], color=AXIS, lw=3, solid_capstyle='round', zorder=2, alpha=.8)
ax.text(-fa[0] - 0.05, -fa[1] - 0.12, 'fast axis of the\nhalf-wave plate', color=AXIS, fontsize=9.5, va='top')
arc(ax, (0, 0), 0.62, 0, al, AXIS, r'$\alpha_{eff}$', 0.95, fs=12)
ph0 = polar(1.7, 0)
ax.plot([0, 1.7], [0, 0], color=POL, lw=0, zorder=0)
phi = 2 * al + 6
pv = polar(1.95, phi)
arrow(ax, (0, 0), pv, POL, lw=3.5)
ax.plot([0, polar(1.95, 45)[0]], [0, polar(1.95, 45)[1]], color=SAMPLE, lw=1.2, ls=':')
ax.text(*polar(2.5, 52), 'balance\n45°', fontsize=9.5, color=SAMPLE, ha='center', va='center')
arc(ax, (0, 0), 1.3, 0, phi, POL, r'$\varphi$', 1.55, fs=13)
arc(ax, (0, 0), 1.75, 2 * al, phi, BEAM, None, lw=2.2)
ax.text(*polar(2.1, (2 * al + phi) / 2 + 3), r'$\theta_K$', color=BEAM, fontsize=12, ha='left', va='center')
ax.text(pv[0] - 0.05, pv[1] + 0.22, 'polarisation', color=POL, fontsize=10.5, fontweight='bold', ha='right')
ax.text(-2.15, -1.25,
        r'$\alpha_{eff}$ = waveplate angle $-$ zero offset (hidden defect)' '\n'
        r'The plate rotates the polarisation by $2\alpha_{eff}$;' '\n'
        r'the sample adds the Kerr rotation $\theta_K$:  $\varphi = 2\alpha_{eff} + \theta_K$' '\n'
        r'$I_A = P\,\sin^2\varphi$,  $I_B = P\,\cos^2\varphi$' '\n'
        r'Balanced when $\varphi$ = 45°, i.e. $\alpha_{eff}$ = 22.5°:' '\n'
        r'$A - B \approx P \sin 2\theta_K$',
        fontsize=9.5, va='top', linespacing=1.5)
ax.text(-2.15, 2.4, 'Waveplate rotation mount:\n' r'$\alpha$ = angle of the plate', color=AXIS, fontsize=10.5, va='top')

fig.suptitle('Angles of the simulated MOKE bench and the plugin that sets each of them', fontsize=14, y=0.995)
fig.tight_layout()
fig.savefig(OUT / 'moke_bench_angles.png', dpi=130)
fig.savefig(OUT / 'moke_bench_angles.svg')

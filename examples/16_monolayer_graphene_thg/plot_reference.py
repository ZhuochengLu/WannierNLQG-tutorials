#!/usr/bin/env python3
"""Render retained THG diagnostics; no response values are synthesized.

Requires NumPy, Matplotlib, Times New Roman and LaTeX with newtx/bm/textgreek.
Each figure records its exact input hashes and PRESENTATION_ONLY qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import os, sys
_CHAPTER = Path(__file__).resolve().parent
sys.path.insert(0, str(_CHAPTER))
import shutil
import os
import subprocess

import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter

BLUE, ORANGE, GREEN, MAGENTA = '#104E8B', '#FF7F24', '#3CB371', '#C71585'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def style():
    font_manager.findfont('Times New Roman', fallback_to_default=False)
    for exe in ('latex', 'pdflatex', 'dvipng', 'kpsewhich'):
        if not shutil.which(exe):
            raise RuntimeError(f'required TeX executable missing: {exe}')
    for name in ('newtxtext.sty', 'newtxmath.sty', 'bm.sty', 'textgreek.sty'):
        if not subprocess.check_output(['kpsewhich', name], text=True).strip():
            raise RuntimeError(f'required TeX package missing: {name}')
    mpl.rc('text', usetex=True)
    mpl.rc('font', family='serif', serif=['Times New Roman'])
    mpl.rcParams.update({'text.latex.preamble': r'\usepackage{newtxtext,newtxmath}\usepackage{bm}\usepackage{textgreek}',
        'font.size': 12, 'axes.labelsize': 14, 'axes.titlesize': 14,
        'xtick.labelsize': 11, 'ytick.labelsize': 11, 'legend.fontsize': 11,
        'axes.linewidth': 1.1, 'lines.linewidth': 1.6, 'figure.facecolor': 'white',
        'xtick.direction': 'in', 'ytick.direction': 'in', 'savefig.dpi': 600})


def axes_pair():
    fig = plt.figure(figsize=(10.8, 4.1), layout='constrained')
    gs = fig.add_gridspec(1, 2)
    axes = [fig.add_subplot(gs[0, i]) for i in range(2)]
    for i, ax in enumerate(axes):
        ax.minorticks_on()
        ax.tick_params(which='both', top=True, right=True)
        ax.text(.03, .96, f'({chr(97+i)})', transform=ax.transAxes, va='top')
    return fig, axes


def legend(ax):
    obj = ax.legend(frameon=True, facecolor='white', edgecolor='#808080', framealpha=.9)
    obj.get_frame().set_linewidth(.8)


def main(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError(f'refusing to overwrite figures: {output}')
    style()
    output.mkdir(parents=True)
    inputs = {}
    def load(temp, mesh, file):
        p = root / 'reference' / f'T{temp}_n{mesh}' / file
        inputs[str(p.relative_to(root))] = sha(p)
        return np.loadtxt(p)
    def save(fig, name, labels):
        # Text-mode minus signs survive independent PDF rendering with newtx.
        for ax in fig.axes:
            if ax.get_yscale() == 'log':
                ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: (
                    r'$10^{\textnormal{' + str(int(round(np.log10(value)))) + r'}}$'
                    if value > 0 else '')))
            if ax.get_xscale() == 'log':
                ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: (
                    r'$10^{\textnormal{' + str(int(round(np.log10(value)))) + r'}}$'
                    if value > 0 else '')))
        fig.savefig(output / f'{name}.png', dpi=600)
        fig.savefig(output / f'{name}.pdf')
        (output / f'{name}.json').write_text(json.dumps(dict(
            qualification='PRESENTATION_ONLY', plot_script_sha256=sha(Path(__file__)), data_qualification='DIAGNOSTIC_ONLY_UNTIL_MATERIAL_CONVERGENCE',
            paper_quantitative_comparison='HOLD_UNRESOLVED_PAPER_NORMALIZATION',
            source_root_relative_to_figures=os.path.relpath(root, output), source_sha256=inputs.copy(),
            formats=['600dpi PNG', 'vector PDF'], typography='Times New Roman; LaTeX newtxtext/newtxmath/bm/textgreek',
            labels=labels, poppler_available=bool(shutil.which('pdftoppm')),
            pdf_visual_inspection='separate QA record; generation alone does not certify rendering'), indent=2)+'\n')
        plt.close(fig)
    xlabel = r'$\hbar\omega\ \mathrm{(eV)}$'
    ylabel = r'$|\Sigma^{(3)}_{yyyy}|\ \mathrm{(A\,m^2/V^3)}$'
    # Native Fourier SI data; no calibrated paper/Dirac overlay while HOLD.
    fig, axes = axes_pair()
    for ax, temp in zip(axes, (10, 300)):
        d = load(temp, 181, 'sigma_yyyy_comparison.dat'); mask = d[:, 0] >= .02
        ax.semilogy(d[mask, 0], d[mask, 5], color=BLUE, label='A4')
        ax.semilogy(d[mask, 0], d[mask, 6], color=ORANGE, ls='--', label='Regrouped')
        for threshold in (2*.35/3, .35, .70):
            ax.axvline(threshold, color='#808080', lw=.6, ls=':')
        ax.set(xlabel=xlabel, ylabel=ylabel, xlim=(.02, 1.2), title=f'{temp} K, $181\\times181$ mesh')
        legend(ax)
    fig.suptitle('Native Fourier SI, spin factor 2; quantitative literature agreement not established', fontsize=12)
    save(fig, 'spectra', [xlabel, ylabel, 'A4', 'Regrouped', '10 K', '300 K'])
    # Keep every coarse mesh, including the large 10 K undersampling excursion.
    fig, axes = axes_pair()
    for ax, temp in zip(axes, (10, 300)):
        for mesh, color in zip((61, 121, 181), (BLUE, ORANGE, GREEN)):
            d = load(temp, mesh, 'sigma_yyyy_comparison.dat'); mask = d[:, 0] >= .02
            ax.semilogy(d[mask, 0], d[mask, 6], color=color, label=f'${mesh}\\times{mesh}$')
        ax.set(xlabel=xlabel, ylabel=ylabel, xlim=(.02, 1.2), title=f'{temp} K, regrouped')
        legend(ax)
    fig.suptitle('Native Fourier SI, spin factor 2; BZ convergence not established', fontsize=12)
    save(fig, 'mesh_scan', [xlabel, ylabel, '61x61', '121x121', '181x181'])
    # At positive real energies, never floor a zero residual to claim a measured value.
    fig, axes = axes_pair()
    for temp, color in zip((10, 300), (BLUE, ORANGE)):
        d = load(temp, 181, 'sigma_yyyy_comparison.dat'); mask = (d[:, 0] > 0) & (d[:, 0] <= .02)
        axes[0].semilogx(d[mask, 0], d[mask, 7] * 1e17, color=color, marker='o', label=f'{temp} K')
        axes[1].semilogx(d[mask, 0], d[mask, 8], color=color, marker='o', label=f'{temp} K')
    axes[0].set(xlabel=xlabel, ylabel=r'$|\Sigma_{A4}-\Sigma_R|/\max(|\Sigma_{A4}|,|\Sigma_R|)$', title=r'Formula residual ($\times 10^{\textnormal{-17}}$)')
    axes[1].set(xlabel=xlabel, ylabel=r'$\sum_s|\Sigma_{A4,s}|/|\Sigma_{A4}|$', title='A4 cancellation ratio')
    for ax in axes: legend(ax)
    fig.suptitle('Fixed causal width 0.010 eV; zero energy retained in tables', fontsize=12)
    save(fig, 'low_frequency', [xlabel, 'Formula residual', 'A4 cancellation ratio', '10 K', '300 K'])
    fig, axes = axes_pair()
    for ax, temp in zip(axes, (10, 300)):
        d = load(temp, 181, 'regrouped_sigma_yyyy_terms.dat'); mask = d[:, 0] >= .02
        for i, (label, color) in enumerate(zip(('Regular', 'Linear pole', 'Quadratic (stored zero)', 'Cubic pole'), (BLUE, ORANGE, GREEN, MAGENTA)), 1):
            valid = mask & (d[:, i] > 0)
            ax.semilogy(d[valid, 0], d[valid, i], color=color, label=label)
        ax.set(xlabel=xlabel, ylabel=r'$|\Sigma_s|\ \mathrm{(A\,m^2/V^3)}$', xlim=(.02, 1.2), title=f'{temp} K, regrouped terms')
        legend(ax)
    fig.suptitle('Term magnitudes do not sum to the total magnitude', fontsize=12)
    save(fig, 'regrouped_terms', [xlabel, 'Regular', 'Linear pole', 'Quadratic pole', 'Cubic pole'])
    print(f'four PNG/PDF pairs written to {output}')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results', default=str(Path(__file__).parent / 'results'))
    p.add_argument('--output', default=str(Path(__file__).parent / 'figures'))
    a = p.parse_args(); main(a.results, a.output)

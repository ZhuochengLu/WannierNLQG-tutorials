#!/usr/bin/env python3
"""Rebuild the Dirac figures from checked data using the bundled NLQG renderer."""
import hashlib
import json
from pathlib import Path
import os, sys
_CHAPTER = Path(__file__).resolve().parent
sys.path.insert(0, str(_CHAPTER))
import subprocess
import sys

import numpy as np
from reference_checks import ROOT, berry, energy, box_flux, write_tsv

FIG = Path(os.environ.get("WANNIERNLQG_FIGURE_OUTPUT", str(ROOT / "figures")))
DATA = Path(os.environ.get("WANNIERNLQG_PLOT_DATA", str(ROOT / "data")))
RENDERER = ROOT.parents[1]/'scripts/plot_support/nlqg_figure.py'
COLORS = ['#104E8B', '#FF7F24', '#3CB371', '#C71585']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(name):
    return np.loadtxt(DATA/f'reference_{name}.tsv', skiprows=1)


def series(name, column, label, color, style='-'):
    return dict(data=str(DATA/f'reference_{name}.tsv'), x_column=0, y_column=column,
                label=label, color=color, linestyle=style)


def panel(xlabel, ylabel, curves, label, **extra):
    return dict(kind='line', label=label, xlabel=xlabel, ylabel=ylabel, series=curves,
                legend_frame=True, legend_fontsize=10, **extra)


def portable_minus(value):
    """Keep negative masses, band labels and inverse units visible in the PDF."""
    if isinstance(value, str):
        return value.replace('^{-1}', r'^{\textnormal{-}1}').replace('m=-', r'm=\textnormal{-}').replace(r'\Omega_-', r'\Omega_{\textnormal{-}}')
    if isinstance(value, dict):
        return {key: portable_minus(item) for key, item in value.items()}
    if isinstance(value, list):
        return [portable_minus(item) for item in value]
    return value


def main():
    checked = json.loads((DATA/'reference.json').read_text())
    if (checked['verified_scopes']['dc_in_gap_platform'] != 'PASS' or
        checked['verified_scopes']['complex_optical_spectrum'] != 'PASS' or
        checked['verified_scopes']['dc_full_axis_benchmark'] != 'PASS' or
        checked['model_source_sha256'] != digest(ROOT/'DiracModel.jl') or
        checked['dc_model_source_sha256'] != digest(ROOT/'DCModel.jl') or
        checked['validator_source_sha256'] != digest(ROOT/'reference_checks.py')):
        raise RuntimeError('reference validation is absent or stale')
    for name, recorded in checked['curve_sha256'].items():
        if digest(DATA/name) != recorded:
            raise RuntimeError(f'stale plot data {name}')
    FIG.mkdir(exist_ok=True)
    k = np.linspace(-.5, .5, 401)
    e = energy(k, 0, .2)
    write_tsv(DATA/'dirac_bands.tsv', ['kx_A_inverse', 'valence_ev', 'conduction_ev'], np.column_stack([k, -e, e]))
    coords = np.linspace(-.4, .4, 161)
    xx, yy = np.meshgrid(coords, coords)
    np.save(DATA/'berry_positive.npy', berry(xx, yy, .2))
    np.save(DATA/'berry_negative.npy', berry(xx, yy, -.2))
    energy_label = r'$\hbar\omega\ (\mathrm{eV})$'
    mu_label = r'$\mu\ (\mathrm{eV})$'
    hall_label = r'$G_H/(e^2/h)$'
    xx_real = r'$\mathrm{Re}\,G_{xx}/(e^2/h)$'
    xx_imag = r'$\mathrm{Im}\,G_{xx}/(e^2/h)$'
    manifests = {}
    band = panel(r'$k_x\ (\mathrm{\AA}^{-1})$', r'$E\ (\mathrm{eV})$',
                 [dict(data=str(DATA/'dirac_bands.tsv'), x_column=0, y_column=i,
                       label=name, color=color) for i, name, color in [(1,'valence',COLORS[0]),(2,'conduction',COLORS[1])]],
                 '(a)', title=r'$m=\pm0.2\ \mathrm{eV},\quad k_y=0$', guide_y=[0])
    maps = [dict(kind='map', label=label, data=str(DATA/f'berry_{name}.npy'),
                 extent=[-.4,.4,-.4,.4], color=dict(kind='diverging', cmap='RdBu_r', limit=50),
                 xlabel=r'$k_x\ (\mathrm{\AA}^{-1})$', ylabel=r'$k_y\ (\mathrm{\AA}^{-1})$',
                 colorbar_label=r'$\Omega_{-}^{xy}\ (\mathrm{\AA}^{2})$',
                 title=title)
            for label,name,title in [('(b)','positive',r'$m=+0.2\ \mathrm{eV}$'),('(c)','negative',r'$m=-0.2\ \mathrm{eV}$')]]
    manifests['dirac_bands_berry'] = dict(kind='grid', rows=1, cols=3, figsize=[15,4.4], panels=[band]+maps)
    curves = []
    for sign, color in [('positive',COLORS[0]),('negative',COLORS[3])]:
        mass_label = r'$m=+0.2$' if sign == 'positive' else r'$m=-0.2$'
        curves += [series('hall_'+sign,3,mass_label+' eV: calculated',color),
                   series('hall_'+sign,7,mass_label+' eV: polar integral',color,'--')]
    manifests['dirac_hall_vs_mu'] = dict(kind='line', figsize=[8,5], xlabel=mu_label,
        ylabel=hall_label, series=curves, guide_x=[-.2,.2], guide_y=[-.5,0,.5],
        ylim=[-.54,.54], yticks=[-.5,-.25,0,.25,.5],
        title=('Anomalous Hall conductance of the Dirac model' + '\n' + r'$K=32\ \mathrm{\AA}^{-1},\ N=6401,\ \gamma=0.002\ \mathrm{eV}$'),
        legend_frame=True, legend_fontsize=10, legend_loc='upper right')
    optical_panels = []
    for col, reference, ylabel, label in [(1,5,xx_real,'(a)'),(2,6,xx_imag,'(b)'),
            (3,7,r'$\mathrm{Re}\,G_H(\omega)/(e^2/h)$','(c)'),
            (4,8,r'$\mathrm{Im}\,G_H(\omega)/(e^2/h)$','(d)')]:
        curves = [series('optical_positive',col,r'$m=+0.2$ eV',COLORS[0]),
                  series('optical_negative',col,r'$m=-0.2$ eV',COLORS[3],'--'),
                  series('optical_positive',reference,'polar integral (+)',COLORS[2],':')]
        if col==1:
            curves.append(series('optical_positive',9,'clean infinite plane','#606060','-.'))
        optical_panels.append(panel(energy_label,ylabel,curves,label,guide_x=[.4],xlim=[0,3],title=r'$K=1,\ N=401,\ \gamma=0.02\ \mathrm{eV}$'))
    manifests['dirac_optical_conductivity'] = dict(kind='grid',rows=2,cols=2,figsize=[11.6,8.6],panels=optical_panels)
    # DC cutoff scan: K and explicitly paired meshes change; gamma stays .002.
    cutoffs=[4.,16.,32.,64.]
    dc_names=['positive_k004','positive_k016','positive','positive_k064']
    computed=[table('hall_'+name)[np.argmin(abs(table('hall_'+name)[:,0])),3] for name in dc_names]
    refs=[table('hall_'+name)[np.argmin(abs(table('hall_'+name)[:,0])),7] for name in dc_names]
    write_tsv(DATA/'cutoff_hall.tsv',['cutoff_A_inverse','computed','finite_gamma_square','clean_box','infinite_plane'],
        np.column_stack([cutoffs,computed,refs,[-box_flux(k,.2) for k in cutoffs],[-.5]*4]))
    cutoff_hall=panel(r'$K\ (\mathrm{\AA}^{-1})$',hall_label,[
        dict(data=str(DATA/'cutoff_hall.tsv'),x_column=0,y_column=i,label=label,color=color,linestyle=style,marker=marker)
        for i,label,color,style,marker in [(1,'Calculated',COLORS[0],'-','o'),(2,'Same-square integral',COLORS[1],'--',None),
          (4,'Clean infinite plane','#606060',':',None)]], '(a)',
        title=r'DC: $\mu=0,\ \gamma=0.002$ eV',xticks=[4,16,32,64],guide_y=[-.5],ylim=[-.501,-.487],
        yticks=[-.5,-.496,-.492,-.488])
    cutoff_panels=[cutoff_hall]
    optical_names=['positive_k025','positive_k050','positive','positive_k200']
    optical_cutoffs=[.25,.5,1.,2.]
    for col,ylabel,label in [(1,xx_real,'(b)'),(2,xx_imag,'(c)')]:
        curves=[series('optical_'+name,col,rf'$K={k:g},\ N={n}$',color)
            for name,k,n,color in zip(optical_names,optical_cutoffs,[101,201,401,801],COLORS)]
        cutoff_panels.append(panel(energy_label,ylabel,curves,label,guide_x=[.4],xlim=[0,3],title=r'Optical: $\gamma=0.02$ eV'))
    manifests['dirac_cutoff_dependence']=dict(kind='grid',rows=1,cols=3,figsize=[15,4.6],panels=cutoff_panels)
    # The full-axis DC mesh test is displayed even when the strict 0.5% test fails.
    platform_curves=[series('hall_positive',3,r'$N=6401$',COLORS[0]),
        series('hall_positive_n9601',3,r'$N=9601$',COLORS[1],'--'),
        series('hall_positive',7,'Same-square integral',COLORS[2],':')]
    mesh_panels=[panel(mu_label,hall_label,platform_curves,'(a)',
        title=r'DC: $K=32,\ \gamma=0.002$ eV',xlim=[-.8,.8],ylim=[-.515,.015],
        yticks=[-.5,-.375,-.25,-.125,0],guide_x=[-.2,.2],guide_y=[-.5])]
    rate=table('hall_positive_g0001');primary=table('hall_positive')
    selected=np.array([np.argmin(abs(primary[:,0]-mu)) for mu in rate[:,0]])
    write_tsv(DATA/'dc_rate_deficit.tsv',['mu_ev','calculated_g002','calculated_g001','integral_g002','integral_g001'],
        np.column_stack([rate[:,0],1e6*(primary[selected,3]+.5),1e6*(rate[:,3]+.5),
                         1e6*(primary[selected,7]+.5),1e6*(rate[:,7]+.5)]))
    curves=[dict(data=str(DATA/'dc_rate_deficit.tsv'),x_column=0,y_column=i,
        label=label,color=color,linestyle=style) for i,label,color,style in [
        (1,r'$\gamma=0.002$ eV',COLORS[0],'-'),(2,r'$\gamma=0.001$ eV',COLORS[1],'-'),
        (3,'Integral (0.002)',COLORS[0],'--'),(4,'Integral (0.001)',COLORS[1],'--')]]
    mesh_panels.append(panel(mu_label,r'$10^6[G_H/(e^2/h)+1/2]$',curves,'(b)',
        title=r'DC: $K=32,\ N=6401$',xlim=[-.12,.12],ylim=[1404,1416],yticks=[1404,1407,1410,1413,1416]))
    curves=[series('optical_'+name,1,rf'$N={n}$',color,style)
        for name,n,color,style in [('positive_n201',201,'#606060',':'),('positive',401,COLORS[0],'-'),('positive_n801',801,COLORS[1],'--')]]
    mesh_panels.append(panel(energy_label,xx_real,curves,'(c)',title=r'Optical: $K=1,\ \gamma=0.02$ eV',guide_x=[.4]))
    curves=[series('optical_positive_n801',1,r'$\gamma=0.02$ eV',COLORS[0]),
        series('optical_positive_g001',1,r'$\gamma=0.01$ eV',COLORS[1]),
        series('optical_positive_g001',5,'Same-square integral (0.01)',COLORS[2],'--')]
    mesh_panels.append(panel(energy_label,xx_real,curves,'(d)',title=r'Optical: $K=1,\ N=801$',guide_x=[.4]))
    manifests['dirac_convergence']=dict(kind='grid',rows=2,cols=2,figsize=[12,8.8],panels=mesh_panels)
    subprocess.run([sys.executable,str(RENDERER),'check-env'],check=True)
    outputs = []
    for stem, figure in manifests.items():
        path = FIG/f'{stem}.plot.json'
        path.write_text(json.dumps(portable_minus(dict(output=dict(stem=stem,dpi=600,formats=['png','pdf']),figure=figure)),indent=2)+'\n')
        subprocess.run([sys.executable,str(RENDERER),'check-glyphs','--manifest',str(path)],check=True)
        subprocess.run([sys.executable,str(RENDERER),'render',str(path)],check=True)
        # Renderer diagnostics use absolute paths internally; public records use chapter-relative paths.
        report = FIG/f'{stem}.summary.json'
        if report.exists():
            report.write_text(report.read_text().replace(str(ROOT),'.'))
        outputs += [FIG/f'{stem}.{ext}' for ext in ('png','pdf')]
    inputs = [ROOT/'DiracModel.jl',ROOT/'DCModel.jl',Path(__file__),RENDERER,DATA/'reference.json'] + \
             sorted(DATA.glob('*.tsv')) + sorted(DATA.glob('*.npy')) + sorted(FIG.glob('*.plot.json'))
    manifest = dict(schema='dirac-figure-hashes-v1',
                    inputs_sha256={os.path.relpath(p,ROOT):digest(p) for p in inputs},
                    outputs_sha256={os.path.relpath(p,ROOT):digest(p) for p in outputs})
    (FIG/'FIGURE_SHA256.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print('DIRAC_FIGURES_OK',len(outputs))


if __name__=='__main__':
    main()

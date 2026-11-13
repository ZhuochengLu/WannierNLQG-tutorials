import os
"""Plot the supplied two-band jerk-current reference comparison without rerunning either kernel."""
from pathlib import Path
import argparse,csv,hashlib,importlib.util,json,math

ROOT=Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--figure',choices=['two_band_analytical_vs_wanniernlqg']);args=parser.parse_args();out=args.output.resolve()
    if out.exists():raise ValueError('fresh output directory required')
    out.mkdir(parents=True)
    spec=importlib.util.spec_from_file_location('retained_style',ROOT/'scripts/plot_support/nlqg_figure.py');nf=importlib.util.module_from_spec(spec);spec.loader.exec_module(nf);nf.configure_profile()
    import matplotlib.pyplot as plt
    import numpy as np
    chapter=ROOT/'examples/17_jerk_current';ref=chapter/'data';sources={};reports=[]
    def rows(path):
        sources[os.path.relpath(path,ROOT)]=hashlib.sha256(path.read_bytes()).hexdigest()
        return list(csv.DictReader(path.open()))
    def save(fig,stem):
        fig.savefig(out/(stem+'.png'),dpi=600,bbox_inches='tight');fig.savefig(out/(stem+'.pdf'),bbox_inches='tight');plt.close(fig)
    if args.figure in (None, 'two_band_analytical_vs_wanniernlqg'):
        raw=rows(ref/'two_band_dense200/analytical_vs_wanniernlqg.csv');assert len(raw)==200;comparison_path=ref/'two_band_dense200/comparison.json';sources[os.path.relpath(comparison_path,ROOT)]=hashlib.sha256(comparison_path.read_bytes()).hexdigest();comparison=json.loads(comparison_path.read_text());photons=[float(r['photon_ev'])for r in raw]
        fig,axes=plt.subplots(2,1,figsize=(7.5,6),sharex=True,layout='constrained',gridspec_kw={'height_ratios':[2,1]});ax=axes[0];ax.plot(photons,[float(r['analytical_physical_sameGaussian_G_bulk'])/1e16 for r in raw],color='black',lw=1.7,label='Analytical reference (same Gaussian)');ax.plot(photons,[float(r['WN_TB513_re'])/1e16 for r in raw],color='#FF7F24',lw=1.2,ls='--',label='WannierNLQG numerical');ax.set(ylabel='Re $G_{bulk}$ ($10^{16}$ A m/V$^3$s$^2$)',title='Two-band model: analytical vs WannierNLQG');ax.legend(fontsize=9);ax.grid(alpha=.2)
        zero_counts={};ax=axes[1]
        for n,color in [(257,'#104E8B'),(513,'#FF7F24')]:
            values=np.array(comparison['errors'][f'two_band_tb_N{n}_eta1.0e-5']['per_energy_complex_error_global_scale']);assert values.shape==(200,)and np.isfinite(values).all()and np.all(values>=0);zero_counts[str(n)]=int(np.count_nonzero(values==0));ax.plot(photons,np.where(values>0,values,np.nan),color=color,lw=1,label=f'N = {n}')
        ax.set(yscale='log',xlabel='Photon energy (eV)',ylabel='Complex error /\nreference amplitude',xlim=(0,4));ax.legend(fontsize=9);ax.grid(alpha=.2);ax.text(.01,.04,'Exact zero errors omitted on log scale',transform=ax.transAxes,fontsize=8)
        for ax in axes:
            for edge in [math.sqrt(2),math.sqrt(10)]:ax.axvline(edge,color='.6',lw=.8,ls=':')
        save(fig,'two_band_analytical_vs_wanniernlqg');reports.append({'figure':'two_band_analytical_vs_wanniernlqg','rows':200,'reference_and_errors':'existing CSV and comparison.json; no reference convolution rerun','zero_error_mask_counts':zero_counts,'zero_mask':'values<=0 on logarithmic display only; raw errors retained'})
    (out/'retained-jerk-report.json').write_text(json.dumps({'scope':'SUPPLIED_DATA_PLOT_ONLY','sources_sha256':sources,'figures':reports,'response_or_reference_kernel_recomputed':False,'new_default_result':False,'style':'Times/TeX; supplied scientific values unchanged'},indent=2)+'\n');print('RETAINED_JERK_FIGURES_RENDERED '+str(len(reports)))

if __name__=='__main__':main()

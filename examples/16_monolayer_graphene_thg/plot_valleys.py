"""Render saved30meV THG conductivity and digitized-paper comparison; no response computation."""
from pathlib import Path
import argparse,hashlib,json,sys,tomllib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
P=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--figure',choices=['magnitude','complex'],required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--data',type=Path,default=P/'data/valley_volume_migration425')
a=parser.parse_args();F=a.output.resolve()
if F.exists():raise SystemExit('Refusing existing figure directory')
F.mkdir(parents=True)
sys.path.insert(0,str(P.parents[1]/'scripts/plot_support'))
from nlqg_figure import configure_profile,environment_report
configure_profile()
contract=json.loads((P/'plot_configs/thg_valley_30meV.json').read_text())
from valley_display_data import load_display_data
D=a.data
current_source=tomllib.loads((P/'valley_input.toml').read_text())['reproduction']['source_manifest_sha256']
u,r,result,height_m=load_display_data(D,contract,current_source)
paper=np.loadtxt(P/'data/paper_fig3a382/display_fourier_si.dat');p=paper[:,[0,1,4,2]]
assert u.shape==r.shape==(84,5)and p.shape==(122,4)
assert np.array_equal(u[:,0],r[:,0])and np.isfinite(u).all()and np.isfinite(r).all()
blue,orange='#104E8B','#FF7F24';figures=[]
def styling(ax):
 ax.tick_params(which='both',direction='in',top=True,right=True);ax.set_xlabel(r'$\hbar\omega/\mu$');ax.grid(False)
def power_tick(value, _position):
 if value == 0: return '0'
 exponent = int(round(np.log10(abs(value))))
 sign = r'\textnormal{-}' if value < 0 else ''
 exponent_text = (r'\textnormal{-}' + str(-exponent)) if exponent < 0 else str(exponent)
 return rf'${sign}10^{{{exponent_text}}}$'
def finish(fig,name):
 for ext in ['png','pdf']:fig.savefig(F/(name+'.'+ext),dpi=600,facecolor='white')
 plt.close(fig);figures.append(name)
if a.figure=='magnitude':
    # Magnitude: full existing84-point spectrum and a12-point computed zoom. Paper's original log polyline, no extrapolation.
    fig,aa=plt.subplots(1,2,figsize=(13.4,5.4),gridspec_kw={'width_ratios':[1.4,1]});fig.subplots_adjust(left=.075,right=.985,bottom=.20,top=.78,wspace=.28)
    fig.suptitle(r'Graphene THG: $30/10/1$ meV resonance/low-frequency/intermediate widths',y=.965,fontsize=15)
    a,b=aa
    for ax in aa:styling(ax)
    a.plot(u[:,1],u[:,4],'-o',color=blue,markersize=3,markerfacecolor='white',linewidth=1.5,label='WannierNLQG unregrouped')
    a.plot(r[:,1],r[:,4],'-s',color=orange,markersize=3,markerfacecolor='white',linewidth=1.5,label='WannierNLQG regrouped')
    a.plot(p[:,1],p[:,2],'--',color='.15',linewidth=1.5,label=r'Paper Fig. 3(a), digitized; causal base $10$ meV')
    a.set_yscale('log');a.yaxis.set_major_formatter(FuncFormatter(power_tick));a.set_ylabel(r'$|\Sigma^{(3)}_{yyyy}|\;[\mathrm{S\,m^2/V^2}]$');a.set_xlim(u[0,1],u[-1,1]);a.set_title('(a) Existing 84-point frequency axis',fontsize=13)
    for x in [2/3,1,2]:a.axvline(x,color='.8',lw=.7,zorder=0)
    mask=(u[:,0]>=.21)&(u[:,0]<=.245)
    for d,c,m in [(u,blue,'o'),(r,orange,'s')]:b.plot(d[mask,1],d[mask,4]/1e-21,'-'+m,color=c,markersize=4,markerfacecolor='white',linewidth=1.6)
    # Display the122-node log10 paper polyline in linear SI, without inventing author samples.
    xx=np.linspace(.21,.245,401);yy=8*6.28e-26*10**np.interp(xx,p[:,0],p[:,3]);b.plot(xx/.35,yy/1e-21,'--',color='.15',lw=1.5)
    local=(p[:,0]>=.21)&(p[:,0]<=.245);b.plot(p[local,1],p[local,2]/1e-21,'x',color='.15',ms=4)
    b.set_xlim(.6,.7);b.set_xticks([.6,.625,2/3,.675,.7]);b.set_xticklabels(['0.600','0.625',r'$2/3$','0.675','0.700']);b.set_ylabel(r'$|\Sigma^{(3)}_{yyyy}|\;[10^{\textnormal{-}21}\,\mathrm{S\,m^2/V^2}]$');b.set_title('(b) Computed local points',fontsize=13);b.axvline(2/3,color='.8',lw=.7,zorder=0)
    h,l=a.get_legend_handles_labels();fig.legend(h,l,loc='upper center',bbox_to_anchor=(.50,.91),ncol=2,fontsize=10,handlelength=2.2)
    fig.text(.075,.075,r'WannierNLQG: two-spin display; distribution broadening, Lorentzian; six finite valley regions with original BZ weights.',fontsize=10)
    fig.text(.075,.035,r'Paper: $8\,\sigma_3\,10^y$, printed $\sigma_3=6.28\times10^{\textnormal{-}26}$; no fitted scale. Full-spectrum convergence is not established.',fontsize=10)
    finish(fig,'thg_valley_magnitude')
if a.figure=='complex':
    # Signed complex components: no paper phase exists in the digitized magnitude trace.
    fig,aa=plt.subplots(1,2,figsize=(13.4,5.2));fig.subplots_adjust(left=.075,right=.985,bottom=.19,top=.78,wspace=.25);fig.suptitle(r'Complex THG conductivity: WannierNLQG $30/10/1$ meV, two-spin display',y=.965,fontsize=15)
    for ax,col,title in zip(aa,[2,3],['(a) Real part','(b) Imaginary part']):
     styling(ax)
     for d,c,m,label in [(u,blue,'o','Unregrouped'),(r,orange,'s','Regrouped')]:ax.plot(d[:,1],d[:,col],'-'+m,color=c,markerfacecolor='white',markersize=3,linewidth=1.5,label=label)
     ax.set_yscale('symlog',linthresh=1e-22,linscale=.5,base=10);ax.yaxis.set_major_formatter(FuncFormatter(power_tick));ax.set_xlim(u[0,1],u[-1,1]);ax.axhline(0,color='.65',lw=.7);ax.set_ylabel(r'$\Sigma^{(3)}_{yyyy}\;[\mathrm{S\,m^2/V^2}]$');ax.set_title(title,fontsize=13)
     for x in [2/3,1,2]:ax.axvline(x,color='.82',lw=.7,zorder=0)
    h,l=aa[0].get_legend_handles_labels();fig.legend(h,l,loc='upper center',bbox_to_anchor=(.53,.90),ncol=2,fontsize=11)
    fig.text(.075,.07,r'Signed-log ordinate: linear inside $\pm10^{\textnormal{-}22}$, logarithmic outside. Markers are actual computed frequencies.',fontsize=10)
    fig.text(.075,.03,'Paper digitization provides magnitude only; no paper real or imaginary curve is inferred.',fontsize=10)
    finish(fig,'thg_valley_complex')
record={'status':'RENDERED_NOT_YET_VISUALLY_REVIEWED','environment':environment_report(),'figures':{n:{ext:dict(path=str((F/(n+'.'+ext)).resolve()),sha256=hashlib.sha256((F/(n+'.'+ext)).read_bytes()).hexdigest())for ext in ['png','pdf']}for n in figures},'data_source_manifest':str((D/'summary.json').resolve()),'volume_to_surface_height_m':height_m,'raw_units':'A*m/V^3','plotted_units':'A*m^2/V^3','new_response_integrations':0,'no_WN_interpolation':True,'paper_display_polyline_not_new_author_data':True,'full_points':84,'new_points':result.get('new_points'),'reused_points':result.get('reused_points'),'symlog_linthresh_SI':1e-22}
(F/'render.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'status':record['status'],'figures':figures}))

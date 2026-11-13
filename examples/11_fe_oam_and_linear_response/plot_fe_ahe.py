#!/usr/bin/env python3
"""Uncentered Fe AHE plane with model-bound Fermi contours and shared signed scale."""
from pathlib import Path
import argparse,hashlib,json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap,FuncNorm
C=Path(__file__).resolve().parent;sys.path.insert(0,str(C.parents[1]/'scripts/plot_support'))
import nlqg_figure as style
FILES={'berry_sos_occupied_xy':'model_bck_sum_conv-288500c6.dat','berry_tb_occupied_xy':'model_bck_sum_conv-d511ca02.dat','berry_transport_equivalent_xy':'linear_transport_berry_curvature-cde8701d.dat'}
TITLES={'berry_sos_occupied_xy':r'Occupied Berry curvature (H/r bundle)', 'berry_tb_occupied_xy':r'Occupied Berry curvature (TB)', 'berry_transport_equivalent_xy':r'Finite-relaxation Berry channel'}
def forward(x):
 x=np.asarray(x);a=np.abs(x);return np.sign(x)*np.where(a<=1,a,1+np.log10(np.maximum(a,1)))
def inverse(x):
 x=np.asarray(x);a=np.abs(x);return np.sign(x)*np.where(a<=1,a,10**(a-1))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--figure',choices=list(FILES),required=True);a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 style.require_environment();style.configure_profile()
 p=C/'data'/FILES[a.figure];raw=np.loadtxt(p)
 if a.figure=='berry_transport_equivalent_xy':
  assert raw.shape==(40000,5)
  # Native table is an unweighted local conductivity kernel in S*m^2.
  coefficient=(1.602176634e-19)**2/1.054571817e-34*1e-20
  z=(-raw[:,3]/coefficient).reshape(200,200)
 else:
  assert raw.shape==(200,200);z=raw.T
 assert np.isfinite(z).all()
 meta=json.loads((C/'data/fe_fermi_plane343.json').read_text());bands=C/'data/fe_fermi_plane343.npz';assert hashlib.sha256(bands.read_bytes()).hexdigest()==meta['array_sha256']
 with np.load(bands)as d:u=d['u'];v=d['v'];energies=d['energy_ev']
 assert energies.shape==(200,200,18)
 colors=[(0,(18,38,170)),(.275,(0,145,205)),(.5,(48,238,43)),(.71,(255,240,55)),(.85,(255,135,20)),(1,(230,30,10))]
 cmap=LinearSegmentedColormap.from_list('fe_zero_green',[(p,np.array(rgb)/255)for p,rgb in colors],N=1025)
 fig,ax=plt.subplots(figsize=(5.0,4.6));fig.subplots_adjust(left=.13,right=.83,bottom=.15,top=.80)
 m=ax.pcolormesh(u,v,z,cmap=cmap,norm=FuncNorm((forward,inverse),vmin=-1e4,vmax=1e4),shading='nearest',rasterized=True)
 count=0
 for b in range(18):
  e=energies[:,:,b]
  if e.min()<0<e.max():ax.contour(u,v,e,levels=[0],colors='black',linewidths=.55);count+=1
 ax.set(xlim=(0,1),ylim=(0,1),xlabel=r'$u$',ylabel=r'$v$',title=TITLES[a.figure]);ax.set_title(TITLES[a.figure],pad=30,fontsize=11);ax.set_aspect('equal');ax.tick_params(direction='in',top=True,right=True)
 for x,y,text in [(0,0,r'$\Gamma(000)$'),(1,0,r'$H(100)$'),(0,1,r'$H(001)$'),(1,1,r'$\Gamma(101)$')]:
  ax.annotate(text,(x,y),xytext=(0,-19 if y==0 else 7),textcoords='offset points',ha='left'if x==0 else'right',va='top'if y==0 else'bottom',fontsize=10)
 ax.xaxis.labelpad=23
 ticks=[-1e4,-1e2,-1,0,1,1e2,1e4];cb=fig.colorbar(m,ax=ax,fraction=.055,pad=.035,ticks=ticks)
 cb.ax.set_yticklabels([r'$-10^{4}$',r'$-10^{2}$',r'$-1$',r'$0$',r'$1$',r'$10^{2}$',r'$10^{4}$']);cb.set_label(r'$\widetilde\Omega^{xy}$ ($\mathrm{\AA}^{2}$)'if a.figure=='berry_transport_equivalent_xy'else r'$\Omega_{\rm occ}^{xy}$ ($\mathrm{\AA}^{2}$)')
 stem=a.output/a.figure;fig.savefig(stem.with_suffix('.png'),dpi=600);fig.savefig(stem.with_suffix('.pdf'));plt.close(fig)
 report={'input_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'fermi_bands':count,'fermi_binding':meta,'grid':[200,200],'coordinates':'uncentered intrinsic u=i/200,v=j/200; pcolormesh and contour share actual nodes; no wrap/stretch/fftshift','linthresh':1,'limits':[-1e4,1e4],'min':float(z.min()),'max':float(z.max()),'clipped_pixels':int(np.count_nonzero(abs(z)>1e4)),'total_pixels':z.size,'response_recomputed':False,'contours_are_model_interpolation_not_material_qualification':True}
 stem.with_suffix('.summary.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()

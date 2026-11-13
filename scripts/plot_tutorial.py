#!/usr/bin/env python3
"""Render only explicitly mapped existing data; never run a numerical tutorial."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def arguments():
    """Require an explicit figure and fresh output for rendering."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--chapter',required=True)
    p.add_argument('--list',action='store_true')
    p.add_argument('--check',action='store_true')
    p.add_argument('--check-renderer',action='store_true')
    p.add_argument('--figure')
    p.add_argument('--output',type=Path)
    p.add_argument('--package-root',type=Path)
    return p.parse_args()


def check_recipe(row):
    """Check declared local dependencies, without importing plotting or Julia runtimes."""
    keys=['script'] if row['engine']in('specialized_script','retained_plot_bundle') else ['recipe']
    paths=[ROOT/row[k] for k in keys]+[ROOT/x for x in row['data']]
    return [str(p) for p in paths if not p.is_file()]


def renderer_script():
    """Use one frozen shared style implementation, not an ambient latest version."""
    return ROOT/'scripts/plot_support/nlqg_figure.py'


def check_renderer_environment():
    """Require the original Times/TeX tools before a first actual render."""
    missing=[name for name in ('kpsewhich','pdflatex','pdftoppm','latex','dvipng') if shutil.which(name) is None]
    if missing:raise RuntimeError('Required Times/TeX renderer tools missing: '+', '.join(missing))
    subprocess.run([sys.executable,str(renderer_script()),'check-env'],check=True)


def prepare_manifest(row,out):
    """Rebase stored inputs; convert explicitly described CSV headers without changing values."""
    import hashlib
    import numpy as np
    path=ROOT/row['recipe'];config=json.loads(path.read_text());conversions=[];cache={}
    def rebase(v,key=''):
        if key=='scale' and not __import__('math').isfinite(float(v)):raise ValueError('Nonfinite recorded series scale')
        if isinstance(v,dict):return {k:rebase(value,k) for k,value in v.items()}
        if isinstance(v,list):return [rebase(value,key) for value in v]
        if isinstance(v,str) and key=='data':
            source=Path(v)
            source=source if source.is_absolute() else (path.parent/source).resolve()
            if not source.is_file():raise ValueError('Missing recorded data: '+str(source))
            if source.suffix.lower()!='.csv':return str(source)
            if str(source) in cache:return cache[str(source)]
            relative=source.relative_to(ROOT).as_posix() if source.is_relative_to(ROOT) else str(source)
            rule=row.get('data_formats',{}).get(relative)
            if rule is None:raise ValueError('CSV requires an explicit recorded header rule: '+relative)
            skip=int(rule['skiprows'])
            if skip:
                first=source.open().readline().rstrip('\r\n')
                if first!=rule['header']:raise ValueError('Recorded CSV header changed: '+relative)
            array=np.loadtxt(source,delimiter=',',skiprows=skip,ndmin=2)
            if not array.size or not np.isfinite(array).all():raise ValueError('Nonfinite or empty CSV')
            converted=out/'staged-data';converted.mkdir(exist_ok=True)
            digest=hashlib.sha256(source.read_bytes()).hexdigest()
            target=converted/(digest+'.npy');np.save(target,array,allow_pickle=False)
            conversions.append({'source':str(source),'source_sha256':digest,'skiprows':skip,
                'shape':list(array.shape),'npy':str(target),'values_or_units_changed':False})
            cache[str(source)]=str(target);return str(target)
        return v
    config=rebase(config)
    config['output']['stem']=str(out/Path(config['output']['stem']).name)
    return config,conversions


def render_manifest(row,out):
    """Delegate the complete stored figure semantics to the frozen original renderer."""
    import hashlib
    config,conversions=prepare_manifest(row,out)
    temporary=out/'render-manifest.json';temporary.write_text(json.dumps(config,indent=2)+'\n')
    subprocess.run([sys.executable,str(renderer_script()),'render',str(temporary)],check=True)
    (out/'render-inputs.json').write_text(json.dumps({'renderer_sha256':hashlib.sha256(renderer_script().read_bytes()).hexdigest(),
        'csv_conversions':conversions,'data_values_or_units_changed':False},indent=2)+'\n')



def render_band_manifest(row,out):
    """Retain common-energy and diagnostic matching semantics in the dedicated band renderer."""
    config,conversions=prepare_manifest(row,out)
    manifest=out/'band-manifest.json';manifest.write_text(json.dumps(config,indent=2)+'\n')
    tool=ROOT/'scripts/plot_support/nlqg_band.py'
    subprocess.run([sys.executable,str(tool),'render',str(manifest)],check=True)
    (out/'render-inputs.json').write_text(json.dumps({'renderer_sha256':__import__('hashlib').sha256(tool.read_bytes()).hexdigest(),'csv_conversions':conversions,'data_values_or_units_changed':False,'material_band_calculation':False},indent=2)+'\n')


def load_reproduction(path):
    """Read the current explicit schema; migration is separate from plotting."""
    info = json.loads(path.read_text())
    if info.get('schema') != 'tutorial-current-case-reproduction/4':
        raise ValueError('Unsupported reproduction schema; explicitly migrate chapter provenance to version 4 before plotting.')
    return info


def main():
    args=arguments();chapter=ROOT/'examples'/args.chapter
    info=load_reproduction(chapter/'reproduce.json');rows=info['figures']
    if args.figure:rows=[r for r in rows if r['id']==args.figure]
    if not rows:raise SystemExit('No mapped figure matches this selection; inspect reproduce.json.')
    if args.check_renderer:
        check_renderer_environment();return
    if args.list or (not args.figure and not args.check):
        print(json.dumps([{'id':r['id'],'related_current_inputs':r['related_current_inputs'],'recorded_execution_inputs':r['recorded_execution_inputs'],'calculation_reproduction_status':r['calculation_reproduction_status'],'figures':r['figures'],
                           'case_association_method':r['case_association_method']} for r in rows],indent=2));return
    missing={r['id']:check_recipe(r) for r in rows}
    if any(missing.values()):raise SystemExit(json.dumps({'MISSING_RECORDED_INPUTS':missing},indent=2))
    if args.check:
        print(json.dumps({'declared_recipes':len(rows),'files_available':True,
                          'numerical_validation':'NOT_RUN','new_default_validation':'NOT_RUN'}));return
    if not args.figure or args.output is None:raise SystemExit('Render requires --figure and --output=NEW_DIRECTORY.')
    out=args.output.resolve()
    if out.exists():raise SystemExit('Refusing existing figure output: '+str(out))
    row=rows[0]
    if row['engine']in('portable_manifest','audited_band_manifest','retained_plot_bundle'):check_renderer_environment()
    out.mkdir(parents=True)
    if row['engine']=='portable_manifest':render_manifest(row,out)
    elif row['engine']=='audited_band_manifest':render_band_manifest(row,out)
    elif row['engine']=='retained_plot_bundle':
        subprocess.run([sys.executable,str(ROOT/row['script']),'--output',str(out/'figures'),*row.get('script_args',[])],check=True)
    elif row['engine']=='specialized_script':
        validation=ROOT/'examples'/args.chapter/'data'
        if validation.exists():shutil.copytree(validation,out/'validation')
        env=dict(os.environ,WANNIERNLQG_FIGURE_OUTPUT=str(out/'figures'),
                 WANNIERNLQG_PLOT_DATA=str(out/'validation'))
        cmd=[sys.executable,str(ROOT/row['script'])]
        if args.chapter.startswith('16_'):
            cmd+=['--results',str(out/'validation'),'--output',str(out/'figures')]
        subprocess.run(cmd,env=env,check=True)
    else:
        if args.package_root is None:raise SystemExit('Legacy package recipe requires explicit --package-root; no source is selected by a mutable latest alias.')
        recipe=ROOT/row['recipe'];config=json.loads(recipe.read_text())
        # Rebase recorded input paths before writing a temporary output-only config.
        def rebase(v,k=''):
            if isinstance(v,dict):return {a:rebase(b,a) for a,b in v.items()}
            if isinstance(v,list):return [rebase(x,k) for x in v]
            if isinstance(v,str) and k in ('input','real','imag','metadata','bands','path','data','eigenval','kpoints','poscar'):
                p=Path(v);return str((recipe.parent/p).resolve()) if not p.is_absolute() else v
            return v
        config=rebase(config);config['output']['stem']=str(out/Path(config['output']['stem']).name)
        temp=out/'plot-config.json';temp.write_text(json.dumps(config,indent=2)+'\n')
        if args.chapter.startswith('10_'):
            subprocess.run([sys.executable,str(ROOT/'scripts/plot_shg_spectrum.py'),str(temp)],check=True)
        else:
            script='plot_band_structure.jl' if args.chapter.startswith('01_') else 'plot_response_integral.jl' if 'integral_' in row['id'] else 'plot_kslice.jl'
            subprocess.run(['julia','--startup-file=no','--project='+str(ROOT),str(args.package_root/'scripts'/script),'--config',str(temp)],check=True)
    (out/'reproduction.json').write_text(json.dumps({'recipe':row,'calculation_rerun':False,
        'same_byte_image_reproduction_claim':False,'data_values_or_units_changed':False,
        'plot_only_band_sampling':row.get('plot_only_band_sampling',False)},indent=2)+'\n')
    print('FIGURE_RENDERED_TO_NEW_DIRECTORY '+str(out))


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Validate and sum saved six-region outputs; never start Julia or a response task."""
from pathlib import Path
import argparse,hashlib,json,math,tomllib

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def rows(path):
    values=[[float(x)for x in line.split()]for line in path.read_text().splitlines()if line.strip()and not line.startswith('#')]
    if not values or any(len(r)!=11 or not all(math.isfinite(x)for x in r)for r in values):raise ValueError('Expected finite11-column native table: '+str(path))
    return values

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,default=Path(__file__).with_name('valley_input.toml'));p.add_argument('--roots',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    spec=tomllib.loads(a.input.read_text());target=spec['spectrum']['target_energies_ev'];expected={(b['id'],r['id'])for b in spec['batches']for r in spec['regions']};records={};source_indexes=[];fixture=False
    for root in a.roots:
        index=root/'index.json';doc=json.loads(index.read_text());fixture=fixture or doc.get('non_execution_fixture',False)
        if doc.get('output_normalization')!='three_dimensional_volume':raise ValueError('Expected explicit periodic volume output normalization')
        if doc['input_sha256']!=digest(a.input)or doc['source_manifest_sha256']!=spec['reproduction']['source_manifest_sha256']or doc['model_sha256']!=spec['reproduction']['model_sha256']:raise ValueError('Input/source/model identity mismatch')
        for rec in doc['records']:
            key=(rec['batch'],rec['region'])
            if key in records:raise ValueError('Duplicate region: '+str(key))
            for f in rec['outputs']:
                q=(root/f['path']).resolve()
                if not q.is_relative_to(root.resolve())or digest(q)!=f['sha256']:raise ValueError('Output path/hash mismatch: '+str(q))
            records[key]=(root,rec)
        source_indexes.append({'root':str(root),'index_sha256':digest(index)})
    if set(records)!=expected:raise ValueError('Missing or unexpected batch/region records')
    total={};diags=[]
    for batch in spec['batches']:
        for rg in spec['regions']:
            root,rec=records[(batch['id'],rg['id'])];paths={Path(f['path']).name:root/f['path']for f in rec['outputs']}
            for form in ['unregrouped','regrouped']:
                for quantity in ['sigma','chi']:
                    name=f'thg_{form}_{quantity}_yyyy.dat';data=rows(paths[name])
                    if[r[0]for r in data]!=batch['energies_ev']:raise ValueError('Frequency vector differs from declared batch')
                    for row in data:
                        v=total.setdefault((name,row[0]),[0.]*10)
                        for j,x in enumerate(row[1:]):v[j]+=x
            d=dict(line.split('=',1)for line in paths['integration_diagnostics.txt'].read_text().splitlines()if '='in line)
            if int(d['initial_divisions'])!=spec['integration']['initial_divisions']or int(d['max_evaluations'])!=rg['max_evaluations']:raise ValueError('Quadrature controls differ')
            diags.append({'batch':batch['id'],'region':rg['id'],'termination':d['termination'],'evaluations':int(d['evaluations']),'requested_max_evaluations':int(d['max_evaluations']),'embedded_estimate':float(d['embedded_estimate']),'not_strict_error_bound':True})
    if len(target)!=len(set(target)):raise ValueError('Duplicate target energies')
    if len(target)!=84 or any((name,e)not in total for e in target for name in ['thg_unregrouped_sigma_yyyy.dat','thg_regrouped_sigma_yyyy.dat','thg_unregrouped_chi_yyyy.dat','thg_regrouped_chi_yyyy.dat']):raise ValueError('Target84incomplete')
    if a.output.exists():raise ValueError('Refusing existing output directory')
    a.output.mkdir(parents=True)
    for form in ['unregrouped','regrouped']:
        for quantity in ['sigma','chi']:
            name=f'thg_{form}_{quantity}_yyyy.dat'
            (a.output/name).write_text('# One-spin volume-normalized native six-region sum; original BZ weights;84target frequencies\n'+''.join(' '.join(format(x,'.17g')for x in[e,*total[(name,e)]])+'\n'for e in target))
        name=f'thg_{form}_sigma_yyyy.dat'
        (a.output/f'wn30_{form}_two_spin.dat').write_text('# energy_eV energy_over_mu real_SI imag_SI magnitude_SI; two-spin volume conductivity A*m/V^3; external surface conversion multiplies by 1e-9 m\n'+''.join(' '.join(format(x,'.17g')for x in[e,e/spec['physics']['fermi_energy_ev'],2*total[(name,e)][0],2*total[(name,e)][1],2*abs(complex(*total[(name,e)][:2]))])+'\n'for e in target))
    summary={'schema':'tutorial-thg-valley-clean-replay/2','target_points':84,'new_points':84,'reused_points':0,'reference_new_points':72,'reference_reused_points':12,'provenance_note':'Reference84source comprises72new402+12reused394G2; this clean collection sums all32vectors. See source_indexes for actual inputs; no reference bitwise identity is claimed.','source_manifest_sha256':spec['reproduction']['source_manifest_sha256'],'model_sha256':spec['reproduction']['model_sha256'],'input_sha256':digest(a.input),'resonance_low_intermediate_eV':[spec['numerics'][k]for k in['broadening','low_frequency_broadening','intermediate_regularization']],'clean_replay_collected_points':84,'clean_replay_computed_unique_energies':len(set(e for b in spec['batches']for e in b['energies_ev'])),'source_indexes':source_indexes,'non_execution_fixture':fixture,'global_convergence_claimed':False,'output_normalization':'three_dimensional_volume','volume_to_surface_height_m':1e-9,'volume_conductivity_units':'A*m/V^3','volume_susceptibility_units':'m^2/V^2','native_spin_copies':1,'display_spin_copies':2}
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(a.output/'integration_diagnostics.json').write_text(json.dumps(diags,indent=2)+'\n');print('COLLECTED84; no response integration executed; fixture='+str(fixture))
if __name__=='__main__':main()

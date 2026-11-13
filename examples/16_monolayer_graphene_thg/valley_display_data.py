"""Read explicitly volume-normalized recorded conversions or clean replay tables."""
from pathlib import Path
import json
import numpy as np

def load_display_data(directory, contract, current_source):
    directory=Path(directory);result=json.loads((directory/'summary.json').read_text())
    if result['target_points']!=84 or result['model_sha256']!=contract['model_sha256']:
        raise ValueError('Target/model identity mismatch')
    if result['resonance_low_intermediate_eV']!=contract['widths_eV'] or contract['widths_eV']!=[.03,.01,.001]:
        raise ValueError('Width identity mismatch')
    if result['schema']=='tutorial-thg-volume-derived/1':
        if result['source_manifest_sha256']!=contract['source_manifest_sha256'] or result['conversion_validation_source_manifest']!=contract['normalization_validation_source_manifest']:
            raise ValueError('Recorded result or conversion-check source mismatch')
        suffix='_volume_derived'
    elif result['schema']=='tutorial-thg-valley-clean-replay/2':
        if result['source_manifest_sha256']!=current_source or result.get('output_normalization')!='three_dimensional_volume':
            raise ValueError('Clean replay source or normalization mismatch')
        suffix=''
    else:
        raise ValueError('Unsupported or unstated data normalization')
    height=float(result['volume_to_surface_height_m'])
    if height!=contract['volume_to_surface_height_m'] or height!=1e-9:
        raise ValueError('Graphene height mismatch')
    arrays=[np.loadtxt(directory/f'wn30_{form}_two_spin{suffix}.dat') for form in ['unregrouped','regrouped']]
    if any(x.shape!=(84,5) or not np.isfinite(x).all() for x in arrays):
        raise ValueError('Expected finite 84 by 5 display tables')
    if not np.array_equal(arrays[0][:,:2],arrays[1][:,:2]) or not np.all(np.diff(arrays[0][:,0])>0):
        raise ValueError('Frequency identity mismatch')
    for x in arrays:x[:,2:]*=height
    return arrays[0],arrays[1],result,height

#!/usr/bin/env python3
"""Rebuild a digitized-paper display only; no WannierNLQG response calculation or amplitude fitting."""
from pathlib import Path
import hashlib,json,math
D=Path(__file__).resolve().parent/'data/paper_fig3a382'
p=json.loads((D/'provenance.json').read_text()); n=p['normalization']; f=D/'digitized_log10.dat'
assert hashlib.sha256(f.read_bytes()).hexdigest()==p['digitization']['raw_sha256']
rows=[list(map(float,line.split()))for line in f.read_text().splitlines()if line and not line.startswith('#')]
assert len(rows)==p['digitization']['nodes']
values=[]
for energy,logmag in rows:
 s=n['sigma3_printed_SI']*10**logmag
 values.append((energy,energy/n['mu_eV'],logmag,s,n['field_conversion_factor']*s))
assert all(math.isfinite(v)for row in values for v in row)
text='# energy_eV energy_over_mu digitized_log10 paper_coefficient_printed_unit_SI converted_Fourier_coefficient_SI\n'
text+=''.join(' '.join(format(v,'.17e')for v in row)+'\n'for row in values)
(D/'display_fourier_si.dat').write_text(text)
print('Rebuilt122 digitized-paper display points; no response calculation or fitted scale.')

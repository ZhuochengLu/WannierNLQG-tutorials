"""Keep the public comparison on the recorded common external transition domain."""
from pathlib import Path
import json
import math
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ShiftDomainTests(unittest.TestCase):
    def test_reference_and_existing_smoke_inputs_use_complete_common_groups(self):
        rows = json.loads((ROOT / 'manifests/current_inputs.json').read_text())
        selected = [r for r in rows if r['chapter'] == '04_kslice_charge_responses'
                    and r['case'].startswith('shift_current_')]
        self.assertEqual({r['case'] for r in selected if r['profile'] == 'reference'},
                         {'shift_current_' + m for m in ('conventional', 'projector', 'wilson_loop', 'geometric_loop')})
        for row in selected:
            task = next(iter(tomllib.loads((ROOT / row['input']).read_text())['response']['tasks'].values()))
            self.assertEqual(task['observable']['valence'], list(range(1, 21)))
            self.assertEqual(task['observable']['conduction'], list(range(21, 33)))
            self.assertEqual(task['photon_energies_ev'], [3.0])

    def test_native_cells_sum_once_to_recorded_same_grid_integral(self):
        document = json.loads((ROOT / 'examples/04_kslice_charge_responses/reproduce.json').read_text())
        for figure in document['figures']:
            if not figure['id'].startswith('kslice_shift_current_'):
                continue
            lines = [line.split() for line in (ROOT / figure['data'][0]).read_text().splitlines()
                     if line.strip() and not line.lstrip().startswith('#')]
            self.assertEqual(len(lines), 200)
            self.assertTrue(all(len(line) == 200 for line in lines))
            values = [float(value) for line in lines for value in line]
            self.assertTrue(all(math.isfinite(value) for value in values))
            reference = figure['provenance']['matched_same_grid_native_integral']['native_integral_Re_yyy']
            self.assertLess(abs(math.fsum(values) - reference), 6e-14)

    def test_withdrawn_gl_qhc_is_not_an_active_case_or_figure(self):
        rows = json.loads((ROOT / 'manifests/current_inputs.json').read_text())
        self.assertFalse(any(r['case'] == 'quantum_hermitian_connection_geometric_loop' for r in rows))
        document = json.loads((ROOT / 'examples/08_shift_geometry/reproduce.json').read_text())
        self.assertFalse(any('quantum_hermitian_connection_geometric_loop' in f['id'] for f in document['figures']))
        self.assertTrue(any(f['id'] == 'kslice_shift_vector_geometric_loop' for f in document['figures']))


if __name__ == '__main__':
    unittest.main()

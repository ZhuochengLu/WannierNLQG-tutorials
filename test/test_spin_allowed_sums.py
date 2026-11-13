#!/usr/bin/env python3
"""Check the published GeS maps against independent, same-mesh tensor integrals."""
from pathlib import Path
import math
import unittest

DATA = Path(__file__).resolve().parents[1] / 'examples/05_kslice_spin_responses/data'


def values(name):
    result = [float(x) for x in (DATA / name).read_text().split()]
    assert len(result) == 200 * 200 and all(map(math.isfinite, result))
    return result


def tensor_component(filename, component):
    lines = (DATA / filename).read_text().splitlines()
    columns = lines[1].split()[3:]
    row = [float(x) for x in lines[2].split()]
    i = columns.index(component)
    return complex(row[2 + 2*i], row[3 + 2*i])


class AllowedSpinMapChecks(unittest.TestCase):
    def test_maps_match_independently_integrated_complex_tensor(self):
        for prefix in ('ssc', 'isc'):
            for component in ('yzxy', 'yzyx'):
                real = values(f'{prefix}_{component}_r_fullbands.dat')
                imag = values(f'{prefix}_{component}_i_fullbands.dat')
                got = complex(math.fsum(real), math.fsum(imag))
                reference = tensor_component(f'{prefix}_fullbands_integral.dat', component)
                self.assertGreater(abs(reference), 0)
                self.assertLess(abs(got-reference)/abs(reference), 1e-7,
                                (prefix, component, got, reference))

    def test_optical_order_symmetry_of_displayed_parts(self):
        for prefix, part, sign in (('ssc','i',1), ('isc','r',-1)):
            a = values(f'{prefix}_yzxy_{part}_fullbands.dat')
            b = values(f'{prefix}_yzyx_{part}_fullbands.dat')
            residual = math.sqrt(math.fsum((x+sign*y)**2 for x,y in zip(a,b)))
            norm = math.sqrt(math.fsum(x*x for x in a))
            self.assertGreater(norm, 0)
            self.assertLess(residual/norm, 1e-9, prefix)


if __name__ == '__main__':
    unittest.main()

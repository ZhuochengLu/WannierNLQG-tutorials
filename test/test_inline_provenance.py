#!/usr/bin/env python3
"""Check lossless inline provenance and reject ambiguous or unsupported records."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from validate_layout import check_inline_provenance

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('tutorial_plot', ROOT / 'scripts/plot_tutorial.py')
PLOT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PLOT)


class InlineProvenanceTests(unittest.TestCase):
    """Exercise valid evidence, mutation, missing identity, and schema rejection."""

    def setUp(self):
        """Use a record with preserved failure and historical qualification fields."""
        payload = {'original_figure_id': 'example', 'response_recomputed': False,
                   'scientific_identity': {'new_default_result': False},
                   'status': 'FAIL', 'previous_selection': {'quality': 'HOLD'}}
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                             separators=(',', ':')).encode('utf-8')
        self.figure = {'provenance': payload, 'provenance_source': {
            'merged_from': 'examples/example/data/example.provenance.json',
            'source_file_sha256': 'a' * 64,
            'payload_sha256': hashlib.sha256(encoded).hexdigest(),
            'encoding': 'json-sort-keys-utf8-compact'}}

    def test_preserves_failure_without_promoting(self):
        """Validation accepts intact FAIL/HOLD evidence and does not mutate it."""
        before = copy.deepcopy(self.figure)
        self.assertEqual(check_inline_provenance(self.figure), 1)
        self.assertEqual(self.figure, before)

    def test_rejects_changed_scientific_status(self):
        """A content change cannot silently inherit the old integrity digest."""
        self.figure['provenance']['status'] = 'PASS'
        with self.assertRaises(AssertionError):
            check_inline_provenance(self.figure)

    def test_rejects_lost_nested_evidence(self):
        """Dropping an old selection fails even when top-level fields remain."""
        del self.figure['provenance']['previous_selection']
        with self.assertRaises(AssertionError):
            check_inline_provenance(self.figure)

    def test_rejects_missing_payload(self):
        """A source receipt without the source data is not complete provenance."""
        del self.figure['provenance']
        with self.assertRaises(AssertionError):
            check_inline_provenance(self.figure)

    def test_rejects_missing_identity(self):
        """Unidentified inline content is not accepted as migrated evidence."""
        del self.figure['provenance_source']
        with self.assertRaises(AssertionError):
            check_inline_provenance(self.figure)

    def test_no_invented_record_for_originally_sidecar_free_figure(self):
        """A figure with separate reference evidence need not gain fake provenance."""
        self.assertEqual(check_inline_provenance({}), 0)

    def test_current_schema_reader(self):
        """The plotting reader consumes the new chapter format."""
        record = {'schema': 'tutorial-current-case-reproduction/4', 'figures': []}
        with patch.object(Path, 'read_text', return_value=json.dumps(record)):
            self.assertEqual(PLOT.load_reproduction(Path('not-opened')), record)

    def test_rejects_legacy_schema(self):
        """Normal plotting never silently falls back to old external sidecars."""
        with patch.object(Path, 'read_text', return_value='{"schema":"tutorial-current-case-reproduction/3"}'):
            with self.assertRaises(ValueError):
                PLOT.load_reproduction(Path('not-opened'))


if __name__ == '__main__':
    unittest.main()

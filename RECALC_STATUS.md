# Fe 1.1.0 recomputation status

**Current update:** the optical-export source repair passed all seven final
engineering gates. The fixed-source 14-case Fe response rerun completed and
replaced the tutorial reference tables after staged numerical/source-hash
checks. The old response tables and optical label correction remain in the
private rollback archive. No material publication qualification is implied.

The earlier fresh Wannierization, fixed-source 14 Fe response references,
VASP/TB path-band comparison, figures, and local bundle asset have been
staged and numerically validated in this isolated candidate. The selected
18-WF model ended at `MAX_ITERATIONS`;
all Fe results remain `DIAGNOSTIC_ONLY / Physics HOLD / Production
NOT_ELIGIBLE`. See [VALIDATION.md](VALIDATION.md) for hashes, metrics, and
gate evidence.

The fixed 1.1.0 source emits optical terms under their native semantic names;
the four new cases have zero numerical difference from the prior corrected
tables. The export-specific local HOLD was cleared after source and tutorial
acceptance, while the Fe physics gate remains HOLD. Both are tracked
separately in [VALIDATION.md](VALIDATION.md). The private raw outputs and prior
SHG＋Fe candidate are retained for rollback. VASP, the original tutorial
checkout, and GitHub were not changed.

# Optional spin runtime data

Injection/shift spin current and Zeeman interband geometry require four additional
files: `GeS.spn`, `GeS.chk`, `GeS.eig`, and `GeS.mmn`. They are distributed as the
GitHub Release asset `GeS_vasp_SOC_spin_runtime_v1.tar.gz` under tag
`ges-vasp-soc-spin-v1` because the overlap file exceeds the regular Git object limit.

Install and verify the bundle from the repository root:

```bash
scripts/download_spin_data.sh
```

The four extracted files are ignored by Git. Their individual hashes are recorded in
`OPTIONAL_SPIN_FILES.json`; the archive hash is recorded in `OPTIONAL_SPIN_SHA256`.

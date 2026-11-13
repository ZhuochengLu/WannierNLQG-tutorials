# Shared tutorial models

TutorialModels.jl is the single callback provider for TOML `model.identity` values.
The Haldane, Rice–Mele, Dirac and graphene files were moved without changing their
physical code or numerical values. GeS and Fe material files remain under Materials.
Task-builder files are retained for expert/test use; ordinary user calculations edit TOML.
Historical source paths and hashes remain recorded in migration/20261108.

Legacy model filenames in chapters are explicit symlinks to these exact shared
files. They preserve historical plot/validator source hashes without duplicating a
model implementation. Ordinary TOML callback loading uses models/ directly; edit
the shared model rather than a legacy filename.

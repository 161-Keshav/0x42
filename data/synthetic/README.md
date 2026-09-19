# Synthetic seed data

All records are invented and use opaque demo IDs. JSON and CSV contain identical
attempts (210 records, 24 students). Expected trend labels are evaluation
metadata, not training inputs. Regenerate with
`python scripts/generate_synthetic.py [--extra N]`.
See `docs/data-contract.md` for the scenarios and their limitations.

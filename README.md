# BrewieNext Procedures

Versioned machine programs for the Brewie B20. This repository contains the
ordered workflows and state-machine procedures executed by the BrewieNext
runner. The editor and runner are tools; this repository is the source code
they modify, validate, package, and execute.

## Layout

- `workflows/` contains top-level entry points and orchestration.
- `procedures/brewing/` contains the standard beer-brewing program.
- `incubator/maintenance/` preserves legacy service programs until they satisfy
  the current language and hardware contracts; incubator files are not shipped.
- `schemas/` pins the supported procedure-language contracts.
- `contracts/` declares the recipe globals and Brewie B20 hardware identifiers
  required by these programs.
- `scripts/` validates source and builds a reproducible flat runtime bundle.
- `tests/` verifies package structure and cross-file references.

## Development

```sh
python3 -m pip install -r requirements-dev.txt
make validate
make test
make bundle
```

Edit source files, run validation, and review the generated manifest before
committing. Never edit `dist/`; release automation rebuilds it from source.

## Versioning

Tags use Semantic Versioning (`v0.1.0`). Increment:

- major for incompatible procedure-language or runtime behavior;
- minor for changed brewing behavior or new programs;
- patch for descriptions, metadata, and behavior-preserving corrections.

The package version in `program-package.yml` must match a release tag. A Brewie
installation consumes an immutable bundle, not a Git checkout.

## Incubator policy

Incubator programs are migration inputs, not executable product code. To
graduate one, replace legacy aliases and unsupported actions, resolve error
handling, add it under `procedures/`, declare it as an entrypoint, and make all
validation and simulation tests pass.

# Public repository boundary

This repository may be public, but public visibility does not grant a license to reuse every referenced dataset or model.

## Included in Git

- Source code, configuration, tests, small audit reports, reproducibility manifests, and derived scalar metrics.
- File lists only when they do not expose private credentials or redistribute restricted source content.
- Attribution and source metadata for public datasets.

## Excluded from Git

- Official competition images and labels.
- Third-party source images or annotations unless redistribution is explicitly allowed and attribution requirements are satisfied.
- Model weights, ONNX exports, training archives, runtime uploads, databases, credentials, `.env` files, and SSH keys.
- Server logs or manifests containing secrets.

Large recoverable artifacts should remain in the training-server backup or a dedicated release/object-storage workflow after a separate license and size review. GitHub is the source-of-truth for code and reproducibility metadata, not a replacement for the raw-data archive.

No project-wide software license has been selected yet. Until the owner adds one, repository visibility alone does not grant downstream reuse rights.

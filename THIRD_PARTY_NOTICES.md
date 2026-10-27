# Third-party notices

The project MIT licence covers original project code and documentation.
It does not replace licences for datasets, models or third-party output.

- **CORD:** NAVER CLOVA; Park et al., *CORD: A Consolidated Receipt Dataset for Post-OCR Parsing* (2019).
  [Dataset](https://huggingface.co/datasets/naver-clova-ix/cord-v2),
  [author repository](https://github.com/clovaai/cord),
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  `evidence/cord-test-24/manifest.json` contains original annotations for test rows 0–23.
  Score and judgment files include derived text and reference excerpts.
  Normalization changes and model errors are recorded separately from the original annotations.
  Receipt images are downloaded into ignored corpus directories, not included in the code package.
- **Nemotron-3.5-Parse:** NVIDIA model and plugin at the revision in `serving/config.json`.
  [Model licence](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/main/LICENSE): OpenMDW-1.1.
  The tokenizer has separate MIT attribution. The container preserves upstream notices.
  Weights and container images are not redistributed by this repository.
- **Synthetic corpus:** original fictional text and layouts are dedicated under CC0-1.0.
  Its manifest records provenance.
- **Elephant–Goldfish:** Google, Apache-2.0. The design reviews use the upstream method and reviewer personas.
  No plugin code is vendored. [Source](https://github.com/google/elephant-goldfish-model).
- **Documentation:** MkDocs Material and dependencies retain their package licences.
  The site uses the same documentation stack as Saucier without copying its product branding.

# RESEARCH NOTE
## Publishing a document to a plain directory

---
**Publisher:** Paperforge Research
**Date:** August 2026

---

## CONTENTS

1. **Context**
2. **Conclusion**

---

## Context {.part}

A document reaches a reader only if it is declared publishable and then clears
the gate. This fixture exists so that path is exercised rather than assumed:
the manifest says what may ship, and lint says whether it is fit to.

The directory target copies the built artefact into a plain folder, which is
what a static host needs and what continuous integration can verify without a
RealTimeX workspace to serve from.

## Conclusion {.part}

Both editions are deliverables. A document that declares a Typst print edition
publishes the reading edition and the print edition as separate artefacts, and
this fixture declares one so that loop runs on every build rather than only on
the machine of whoever happens to be releasing.

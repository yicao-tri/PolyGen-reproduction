# Full-source PI1M near-overlap audit status

Status: **blocked by missing external input; no result inferred**.

The package contains an exploratory 1-in-10 systematic PI1M audit under
`evidence/data/pi1m_near_overlap/`. A full-source rerun was attempted against
the recorded source path `/tmp/pi1m/PI1M_v2.csv`, but that file is no longer
present on the current host and no second copy was found under `/Users/yicao`.
The full-source audit therefore produced no output table or summary. The
existing sampled result must not be re-labeled as a full-source absence proof.

Once the external source is restored, run:

```text
/Users/yicao/Documents/ARC/PolyGen-reproduction/.venv/bin/python \
evidence/scripts/pi1m_near_overlap_audit.py \
  --canonical-root /Users/yicao/Documents/ARC/PolyGen-reproduction \
  --pi1m /tmp/pi1m/PI1M_v2.csv \
  --output-dir evidence/data/pi1m_near_overlap_full \
  --sample-stride 1
```

The PI1M source is external and is not redistributed in this package.

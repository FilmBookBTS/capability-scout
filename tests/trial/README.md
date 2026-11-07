# v0.3.2 supervised trial files (historical)

These files belong to the v0.3.2 trial with a person present (ledger batch
`legacy-v0.3.2-supervised-mac`). They are kept as a record, not as current instructions. For
current tests, see [`docs/TEST_METHOD.md`](../../docs/TEST_METHOD.md).

They are kept for two reasons:

- [`LIVE-TRIAL.md`](LIVE-TRIAL.md) is the procedure behind that ledger row. The offline test
  [`tests/offline/test_pasted_and_followups.py`](../offline/test_pasted_and_followups.py) reads its
  prompts from this file.
- [`trial-settings.json`](trial-settings.json) holds the session-only permission rules used in that
  trial. The earlier harness [`tests/live-legacy/run_matrix.py`](../live-legacy/run_matrix.py) uses
  it for its `T-trial` condition.

Change made for publication: `trial-settings.json` listed the names of 16 connector tools from
the test account. They are replaced with two generic examples (`mcp__example_chat_connector`,
`mcp__example_email_connector`). Nothing else changed. SHA-256 of the file as used in the trial:
`df7726bbbdacbbb58dda002eacee0b1e63c9bb3f628da44d1cba983e639be63b`; as published:
`8ef16e9292e32e5579b5037cc48152e63a8efe4ecb282a440494ff69b6a67768`.

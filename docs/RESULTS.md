# Results

The full results are generated from the ledger and kept in one place:
[`results/RESULTS.md`](../results/RESULTS.md). That page is rebuilt by
[`tools/summarize.py`](../tools/summarize.py) from [`results/ledger.csv`](../results/ledger.csv),
one row per test session, so it cannot disagree with the data.

- How the tests were run: [TEST_METHOD.md](TEST_METHOD.md).
- What was decided before the live test, including the pass criteria: [ANALYSIS_PLAN.md](ANALYSIS_PLAN.md).
- Each live run's settings, commit and session order: `results/runs/<run id>/manifest.json`.

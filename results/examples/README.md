# Example replies from the live test

Each file is the final reply of one live-test session, copied byte for byte from the session's
raw record (`results/runs/<run id>/raw/<seq>/final.txt`, kept in the backups, not in this
repository). The harness stores at most the first 4,000 characters of a reply; these three are
shorter than that, so they are complete. They contain no private data.

| File | Ledger row (`run_id`) | Task | Setup | Model |
|---|---|---|---|---|
| [ts1-stage1-default-ABC-0213.txt](ts1-stage1-default-ABC-0213.txt) | `20261105T230924Z-ts1-stage1-default-ABC:0213` | P1-security | no plugin (arm A) | claude-sonnet-5-5 |
| [ts1-stage1-default-ABC-0328.txt](ts1-stage1-default-ABC-0328.txt) | `20261105T230924Z-ts1-stage1-default-ABC:0328` | P1-security | plugin as published (arm C) | claude-sonnet-5-5 |
| [ts1-stage1-default-ABC-0070.txt](ts1-stage1-default-ABC-0070.txt) | `20261105T230924Z-ts1-stage1-default-ABC:0070` | P3-missing | plugin as published (arm C) | claude-sonnet-5-5 |

The prompts are in [`tests/live/tasks.json`](../../tests/live/tasks.json). The files in the
sessions' working folder are in [`tests/fixture`](../../tests/fixture).

SHA-256 of each file, which matches the raw record:

```
d6cae91ea3b5b449d112ef8ec0ccac6fba0924ccfd9a58856f0626ecf71b3ed1  ts1-stage1-default-ABC-0213.txt
32c651c4b5dfa606029da3f145ff217aba19ee2a236d531b4fb2fcdd2bba99c7  ts1-stage1-default-ABC-0328.txt
7551d8ca177493dc888f1062b7238ba13c6c987fe165ad6e3ef45b44b48f8014  ts1-stage1-default-ABC-0070.txt
```

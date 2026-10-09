# AI usage

CompPulse was implemented with coding agents working from `docs/prompts/` on the DAG in `docs/build-dag.md`.

- Level 0 and level 1 landed as merge commits on `main`. The agents did not squash.
- The directory, dashboard, and profile screens were separate pull requests. Each screen reads the backend payload for that request.
- GitHub Actions does not start, because the account billing limit blocks the jobs. The checks that ran are local: `ruff`, `pytest` (86 passed), `tsc --noEmit`, and the Compose smoke on `127.0.0.1:65525`.
- `scripts/check_perf.py` recorded the 100,000-row numbers in `docs/performance.md`. Those figures are from that process, not from a model guess.
- `docs/verification-report.md` and `docs/verification-report.html` quote the captured logical, launch, end-to-end, UI, and load logs. The profile section says which paths are not O(1).
- The demo video is not recorded here. The spoken script is in the README. A person records it.

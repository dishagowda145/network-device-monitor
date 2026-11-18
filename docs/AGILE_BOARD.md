# Agile Board: Tasks and Acceptance Criteria

Create these as GitHub Issues (run `scripts/create_issues.sh`, or add them by hand), put them on a **GitHub Projects** board with columns *Todo, In progress, Done*, and close each one from a pull request (`Closes #3` in the PR description).

Working style to describe in interviews: small tasks, one branch per task, a short pull request, tests green in CI, then merge.

| # | Task | Labels | Acceptance criteria |
| --- | --- | --- | --- |
| 1 | Database schema and device endpoints with validation | backend | Bad host, port and name are rejected; duplicate host and port gives 409. |
| 2 | TCP check function and unit tests | backend,testing | Tests use a local TCP server (up) and a closed port (down). |
| 3 | Background monitor and alerts on state change | backend | Tests show one alert per change, none for repeated same state. |
| 4 | SSRF protection for public deployment | security | Guard tests pass; setting is on in render.yaml. |
| 5 | Design all screens in Figma | design | Desktop and mobile frames for every screen; link added to README. |
| 6 | React dashboard: summary, add form, device cards | frontend | Cards show up, down and unknown states. |
| 7 | History panel and alerts list | frontend | Matches the Figma history row; mobile layout wraps correctly. |
| 8 | Match the UI to the Figma design | frontend,design | Desktop (1440) and mobile (375) match; side-by-side screenshots in docs/screenshots. |
| 9 | Accessibility pass | frontend | No contrast failures; usable with keyboard only. |
| 10 | Deploy a demo and add the link | devops | Live link in README. |
| 11 | Write user and technical documentation | docs | A new teammate can run, use and understand the app from the docs. |

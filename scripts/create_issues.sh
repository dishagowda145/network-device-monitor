#!/usr/bin/env bash
# Creates the project issues on GitHub. Needs the GitHub CLI: https://cli.github.com (run `gh auth login` once).
# Run from inside your cloned repo:  bash scripts/create_issues.sh
set -e

gh label create "backend" --force >/dev/null
gh label create "design" --force >/dev/null
gh label create "devops" --force >/dev/null
gh label create "docs" --force >/dev/null
gh label create "frontend" --force >/dev/null
gh label create "security" --force >/dev/null
gh label create "testing" --force >/dev/null

gh issue create --title "Database schema and device endpoints with validation" --label "backend" --body $'Add, list and delete devices with validated input.\n\n**Acceptance criteria**\n- Bad host, port and name are rejected; duplicate host and port gives 409.'
gh issue create --title "TCP check function and unit tests" --label "backend,testing" --body $'check_tcp returns up or down with response time or error.\n\n**Acceptance criteria**\n- Tests use a local TCP server (up) and a closed port (down).'
gh issue create --title "Background monitor and alerts on state change" --label "backend" --body $'Thread checks every device on an interval and writes alerts only when state changes.\n\n**Acceptance criteria**\n- Tests show one alert per change, none for repeated same state.'
gh issue create --title "SSRF protection for public deployment" --label "security" --body $'Refuse private and local addresses when BLOCK_PRIVATE_HOSTS=1.\n\n**Acceptance criteria**\n- Guard tests pass; setting is on in render.yaml.'
gh issue create --title "Design all screens in Figma" --label "design" --body $'Create the Figma file from docs/FIGMA_DESIGN_SPEC.md.\n\n**Acceptance criteria**\n- Desktop and mobile frames for every screen; link added to README.'
gh issue create --title "React dashboard: summary, add form, device cards" --label "frontend" --body $'Live status with 10 second refresh.\n\n**Acceptance criteria**\n- Cards show up, down and unknown states.'
gh issue create --title "History panel and alerts list" --label "frontend" --body $'Dots, times and response-time bars; alert feed.\n\n**Acceptance criteria**\n- Matches the Figma history row; mobile layout wraps correctly.'
gh issue create --title "Match the UI to the Figma design" --label "frontend,design" --body $'Compare each frame to the page in Dev Mode and fix differences.\n\n**Acceptance criteria**\n- Desktop (1440) and mobile (375) match; side-by-side screenshots in docs/screenshots.'
gh issue create --title "Accessibility pass" --label "frontend" --body $'Contrast, labels, focus rings, tap targets; status not shown by colour alone.\n\n**Acceptance criteria**\n- No contrast failures; usable with keyboard only.'
gh issue create --title "Deploy a demo and add the link" --label "devops" --body $'Deploy with render.yaml.\n\n**Acceptance criteria**\n- Live link in README.'
gh issue create --title "Write user and technical documentation" --label "docs" --body $'Keep docs/ up to date.\n\n**Acceptance criteria**\n- A new teammate can run, use and understand the app from the docs.'

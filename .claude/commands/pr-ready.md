---
description: Summarise the working diff as a PR description
allowed-tools: Bash(git diff:*), Bash(git status:*), Bash(git log:*)
---

Read the current diff and write a PR description using `.github/pull_request_template.md`. Say which section or demo tab the change shows up in. If the diff mixes unrelated changes, say how to split it into smaller PRs. Then run the code-reviewer agent on the same diff and list anything it finds.

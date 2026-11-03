# Privacy

- **Local only.** money-coach reads files you give it and writes to `./money-coach-data/` in your working folder. No telemetry, no uploads, no accounts. The only network access is the optional Cashflow MCP you've connected yourself, and only for read queries.
- **The dashboard server** binds to `127.0.0.1`, rejects requests whose Host or Origin isn't your machine, accepts JSON writes only, and writes files atomically with permissions `600`. A daily backup is kept in `money-coach-data/backups/`.
- **Never stored:** passwords, full card or account numbers, credentials. Onboarding asks for card *names* only.
- **What's stored:** your transactions (as exported by your bank), your onboarding answers, findings, and dashboard edits. All of it is plain CSV/JSON you can read.
- **Delete everything:** remove the `money-coach-data/` folder.
- **Don't commit it.** If your working folder is a git repo, add `money-coach-data/` to `.gitignore`. `/money-review` checks and offers to do this.
- **Sharing:** the Excel workbook and `site/index.html` contain your data. Don't upload them anywhere public.

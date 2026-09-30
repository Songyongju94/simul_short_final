# Secret handling

- Never read, print, attach, or search the contents of `.config` or its backups.
- Exclude `.config` and `.config.*` from repository-wide content searches.
- Never retrieve credentials from Git history, the index, environment variables, logs, or other copies.
- Never request elevated access to bypass a secret-file access denial.
- Do not run the live trading service to test changes. Use dummy credentials for isolated tests.
- These instructions supplement sandbox permissions; they are not an access-control boundary.
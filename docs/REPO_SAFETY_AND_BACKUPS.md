# Repo Safety & Backups

This repo (`pr_checker/`) is **tools + docs only**. Your actual project repositories live at workspace level in `../repos/`.

## Why this matters

Commands like `git clean -fdx` will delete **ignored files and folders**. If you keep local repos inside a tool repo and someone runs an aggressive clean, you can lose work.

Keeping repos at `../repos/` avoids coupling them to `pr_checker` git operations.

## Backups

Backups are handled by a workspace-level script (outside `pr_checker/`), so it won't get swept up in tool repo operations:

- Script: `/home/tiago/scripts/backup_workspace.sh`
- Backs up: `/home/tiago/repos` and `/home/tiago/pr_checker`
- Output: `/home/tiago/backups/pr_checker/workspace-<timestamp>.tar.gz`
- Retention: configurable (default 14 days)
- Hard rule: excludes `node_modules`

Run it manually:

```bash
/home/tiago/scripts/backup_workspace.sh
```

Restore example:

```bash
mkdir -p /home/tiago/restore_test
tar -xzf /home/tiago/backups/pr_checker/workspace-YYYYMMDDTHHMMSS.tar.gz -C /home/tiago/restore_test
```

## Cron (recommended)

Edit crontab:

```bash
crontab -e
```

Daily at 02:15:

```cron
15 2 * * * /home/tiago/scripts/backup_workspace.sh >> /home/tiago/backups/pr_checker/backup.log 2>&1
```

## Extra belt-and-suspenders options

- Add `repos/` to VS Code workspace root, not inside `pr_checker/`.
- Prefer `git clean -fd` (without `-x`) unless you *really* mean it.
- Consider a systemd timer if you want better logging and missed-run handling.

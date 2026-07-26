# mbp-backups

A tiny safety net against coding agents (or you) accidentally deleting files
on your Mac — using the APFS snapshot machinery that's already built into
macOS. No sandboxes, no kernel extensions, no third-party backup daemons.

There have been real incidents of coding agents wiping users' home
directories. Sandboxing tools prevent this but are annoying to live with.
This takes the ZFS-style approach instead: **frequent, automatic,
copy-on-write snapshots** that a runaway `rm -rf` cannot touch, with
recovery through macOS's native interfaces.

## How it works

macOS can take **APFS local snapshots** — the same instant, near-zero-cost,
copy-on-write snapshots Time Machine uses (`tmutil localsnapshot`). They are:

- **Immutable from userspace.** A process deleting your files — even as
  root — cannot delete the snapshots. Only `tmutil` can, and only with
  root for deletion.
- **Browsable in the native "Enter Time Machine" UI**, mountable read-only
  for surgical file recovery, and usable as a **full-volume restore source
  from macOS Recovery** — even with no Time Machine backup disk configured.
- **Free-ish.** Copy-on-write means a snapshot only consumes space as files
  change after it was taken.

This repo installs a launchd agent that snapshots every 20 minutes
(configurable).

## Install

```bash
git clone https://github.com/slim-bean/mbp-backups.git
cd mbp-backups
./install.sh
```

That's it. Runs as your user, no sudo. To snapshot every 10 minutes instead:

```bash
SNAPSHOT_INTERVAL_SECONDS=600 ./install.sh
```

Remove it with `./uninstall.sh`.

## Recovering files

**A file or directory was deleted:**

1. `bin/list-snapshots` — pick a snapshot from before the damage.
2. `bin/mount-snapshot [name]` — mounts it read-only (defaults to the most
   recent); copy your files back out from
   `$TMPDIR/mbp-backups-snapshot/Users/<you>/...`.

Or just open Time Machine (menu bar → "Browse Time Machine Backups") and
step back — these snapshots appear there natively.

**The machine is badly broken / won't get to your desktop:**

1. Boot into macOS Recovery (hold the power button on Apple Silicon;
   Cmd-R on Intel).
2. Choose **Restore from Time Machine Backup**. Local snapshots on the
   internal disk appear as restore sources — no external disk needed.
3. Pick the snapshot from before the agent ran. This rolls the entire Data
   volume (home dir, apps, settings) back to that moment.

Note that on modern macOS the OS itself boots from the sealed, read-only
Signed System Volume, so an agent can't actually delete `/System` — the
damage it can do is to the Data volume, which is exactly what these
snapshots cover. Worst case, "Reinstall macOS" from Recovery rebuilds the
system without touching your data.

Want a restore point taken right before an agent session instead of (or on
top of) the schedule? Wrap your agent in a shell function that runs
`bin/take-snapshot` first.

## Limitations — read this part

APFS local snapshots are an **undo buffer, not a backup**:

- **They expire after ~24 hours.** macOS auto-thins them; there is no
  supported way to pin them or extend retention. If you notice the damage
  two days later, the snapshots are gone.
- **They live on the same disk.** A dead SSD, a reformat, or an agent with
  passwordless sudo running `diskutil eraseDisk` takes the snapshots with
  it. (Also: don't give agents passwordless sudo.)
- **Disk pressure purges them early.** If the disk fills up, macOS deletes
  local snapshots to make room.

So keep a real, off-device backup for anything that matters beyond a day —
restic/kopia/Arq to a NAS or cloud, or rsync to a ZFS box that snapshots
server-side. This tool covers the gap those don't: the five minutes between
"agent started" and "agent deleted the wrong thing."

## License

Apache 2.0 — see [LICENSE](LICENSE).

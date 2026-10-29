# Alerting when snapshots stop

If you ship telemetry to Grafana Cloud (or any Prometheus + Loki pair) with
[Grafana Alloy](https://grafana.com/docs/alloy/latest/), you can get paged
when snapshots stop happening — without false alarms every time your laptop
is asleep or traveling.

`take-snapshot` already writes a heartbeat log,
`~/Library/Logs/mbp-backups/snapshots.log`, with one `OK` or `FAIL` line per
snapshot attempt. The log is append-only between rotations: before an attempt,
if it has reached 1 MiB, it is renamed to `snapshots.log.1` (replacing the
previous archive). Alloy can finish reading the old file and follow the new
`snapshots.log`; keep the file target exact, not a glob including archives,
to avoid replaying old heartbeats. Do not rewrite the active log each run:
that causes old entries to be ingested again with fresh timestamps.

The setup here is:

1. **Tail that log into Loki** ([pipeline.alloy](pipeline.alloy)). If you use
   Fleet Management, add it as a pipeline scoped to your laptop's collector
   (e.g. matcher `collector.ID="<your-collector>"`); otherwise drop it into
   your local Alloy config. Note: this avoids the node_exporter textfile
   collector on purpose — `prometheus.exporter.unix` is a singleton in Alloy
   and is often already claimed by a macOS integration pipeline.
2. **Alert on "online but not snapshotting"**
   ([alert-snapshots-stopped.json](alert-snapshots-stopped.json)). The rule
   only fires when both are true:
   - Alloy self-metrics show the machine is up (Prometheus):

     ```promql
     count(alloy_build_info{collector_id="<your-collector>"}) or vector(0)
     ```

   - Zero `OK` lines in the last 2 hours (Loki):

     ```logql
     sum(count_over_time({job="mbp-backups", instance="<hostname>"} |= ` OK ` [2h])) or vector(0)
     ```

   The laptop being closed/offline makes the first query 0, so the rule
   stays quiet. A 15m pending period absorbs the wake-from-long-sleep race
   where liveness returns before the first snapshot line ships.
3. **Alert fast on `FAIL` lines**
   ([alert-snapshots-failing.json](alert-snapshots-failing.json)) — the
   launchd agent is running but `tmutil` itself is erroring.

Create the rules with the Grafana provisioning API (or click them together
in the UI from the queries above):

```bash
# fill in folderUID and datasource UIDs in the JSON first
gcx api /api/v1/provisioning/alert-rules -H 'X-Disable-Provenance: true' \
  -d @observability/alert-snapshots-stopped.json
```

Both example rules use `noDataState: OK` / `execErrState: OK` — tuned for
quiet over paranoid, since transient datasource hiccups on a personal stack
shouldn't page you. Flip them to `Alerting` if you'd rather fail loud.

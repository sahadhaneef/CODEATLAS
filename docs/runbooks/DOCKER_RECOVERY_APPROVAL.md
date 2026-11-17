# Docker startup diagnosis and proposed recovery — 2026-10-30

Status: procedure prepared for approval; recovery actions have NOT been executed.
Phase 1 remains in progress. No reset, prune, VHD move, filesystem mount/repair, Docker/WSL
shutdown/restart, system setting change or backup copy was performed during this diagnosis.

Approval update: the user approved the backup-first shutdown, one controlled startup and
Desktop-managed relocation to D:, subject to saving WSL work first, verified stopped-VHD backup
hashes, and the stated capacity requirements. The approved preflight found C: at **3.86 GiB**
free, below the **10-GiB** restart margin; D: had **213.52 GiB** and E: **158.00 GiB** free.
Recovery therefore stopped before shutdown or backup. No work was interrupted. Conditional
approval remains recorded, but does not authorize proceeding below the margin or cleaning C:.
Saved-work confirmation and backup/hash verification are still required before later steps.

## Findings from read-only checks

- Docker Desktop file version: 4.93.0.240920; CLI 29.8.1; context desktop-linux.
- Data VHD: `C:\Users\Sahad\AppData\Local\Docker\wsl\disk\docker_data.vhdx`,
  9,496,952,832 bytes (8.84 GiB), last modified 2026-10-30 14:47:47 local time.
- Runtime VHD: `C:\Users\Sahad\AppData\Local\Docker\wsl\main\ext4.vhdx`,
  100,663,296 bytes (96 MiB). Neither file has the Windows read-only attribute.
- Settings at `C:\Users\Sahad\AppData\Roaming\Docker\settings-store.json` do not show an
  alternate disk location. Existing Linux images, volumes and containerd data remain on C:.
- Available host space at inspection: C: 4,153,237,504 bytes (3.87 GiB),
  D: 229,282,291,712 bytes (213.54 GiB), E: 169,649,008,640 bytes (158.00 GiB).
  Recheck before any action; these numbers change. All three volumes report NTFS/Healthy.
- C: and E: are partitions of physical disk 0. D: is on physical disk 1. Prefer D: for both
  live Docker storage and the initial offline backup; E: is a capacity fallback, not a
  physically independent backup of C:.
- Ubuntu and docker-desktop are registered as WSL 2 and currently stopped. Windows WslService
  and vmcompute are running. Docker Desktop/backend processes remain running, but `docker
  version` cannot reach a functioning server: Docker Desktop is unable to start. This can
  reflect a retained failure state; no new controlled restart was attempted.
- No matching recent disk/NTFS/WSL warning/error was returned by a bounded query of 60 recent
  System warning/error events over eight hours. This does not prove physical hardware health
  or absence of older/unqueried events. Get-VHD is unavailable; virtual capacity, guest free
  space, current disk attachment and offline filesystem integrity remain unverified.

## Cause: established versus uncertain

The initiating storage shortage is confirmed, not just inferred from low free space:

1. VM log `C:\Users\Sahad\AppData\Local\Docker\log\vm\init.log`, around lines 3845–3865,
   records write I/O failures, an aborted ext4 journal, a failed superblock write and a
   read-only remount at **14:44:37 IST** (09:14:37 UTC).
2. Containerd then fails writing both overlay snapshot metadata and
   `/var/lib/desktop-containerd/daemon/io.containerd.metadata.v1.bolt/meta.db`. PostgreSQL
   container logging also records a read-only filesystem error. Failed image export was a
   consequence of this storage state, not evidence of a Python build dependency failure.
3. Host `monitor.log`, around lines 4491–4558, reports insufficient space writing Docker logs
   and a Disk full error report at **14:46:47–14:46:54 IST**. Electron logs also record ENOSPC.
   The earlier CodeAtlas test run separately observed approximately 7 MiB free on C:.
4. Shutdown reported inability to detach the VHD cleanly and suggested WSL shutdown. This is
   further reason to quiesce and back up before trying recovery.

Conclusion: **confirmed host disk exhaustion, with a confirmed ext4 journal abort/read-only
fallback and potential filesystem/data damage**. The likely causal chain is exhausted backing
storage → guest write failure → journal abort → read-only remount → containerd/engine failure.
Permanent containerd/Bolt database corruption is NOT established: its observed errors say
read-only, not checksum/page corruption. Physical disk failure is not established either.
Current free space does not prove the journal, interrupted image exports or databases recovered.
Do not delete meta.db, rename storage directories, force read-write mounts or repeatedly restart.

## Proposed destinations and space budget

Approval targets:

- Cold backup: `D:\CodeAtlas\backups\docker\20261030-<unique-run-id>`.
- Live Docker data, moved only by Desktop's supported setting: `D:\CodeAtlas\DockerDesktop`.
- Additional working repair copy if needed: a separate directory under the backup root.
- If D: cannot meet measured peak usage, propose corresponding new E:\CodeAtlas folders
  and obtain the required filesystem permission; do not silently change the target.

The two observed VHD file lengths total about 8.94 GiB. Budget at least 10 GiB for the cold
copy, another 10 GiB for a possible working copy, and approximately 10 GiB for relocation,
plus at least 20 GiB operational growth/headroom: **reserve 50 GiB free on D:** for this plan.
This is a conservative working budget, not a vendor sizing guarantee. Verify actual allocated
and copied sizes; sparse-file copies can consume more physical space than the source allocation.
Logical database dumps/image exports need additional measured space and are not included.
The initial D: backup is physically separate from the original on C:, but after relocation
that backup and the live disk would share disk 1. Keep another independently stored backup
for hardware-loss protection; no additional copy destination or backup upload is authorized
or created by this proposal.

C: still needs space for Windows, Docker Desktop runtime/logs and WSL startup. Target **10 GiB
free on C:** before a controlled restart as an operational precaution, not a Docker-published
minimum. Current 3.87 GiB is below that target. No cleanup items have been approved. If reaching
that target requires deleting or moving other data, stop and request approval for those exact
items; do not prune Docker or expand a disk to disguise a full Windows host volume.

## Procedure for approval (not executed)

1. **Quiesce and take an offline backup.** Save all WSL work, including unrelated Ubuntu jobs.
   Quit Docker Desktop normally. With approval, run `wsl --shutdown`; this affects every WSL
   distribution, not just CodeAtlas. Verify Desktop/backend processes have exited and VHDs
   are no longer in use. If a handle remains locked, stop rather than force-kill/copy a live
   database. A Windows reboot may be needed, but is not automatically required or authorized.
2. **Copy, never move, the stopped disks for backup.** Copy docker_data.vhdx to the unique D:
   backup directory with the same filename; also preserve main/ext4.vhdx as a separate runtime
   backup and Docker settings. Docker's documented failed-start backup is the data VHD. Record
   paths, file sizes, timestamps and SHA-256 of source and backup while stopped; retain a
   read-only-by-convention untouched backup. This captures existing damage too; a matching hash
   is copy integrity, not proof that images/databases are healthy. Preserve project Compose
   files and `.env`/source encryption key separately with restricted access; never print keys.
   Bind-mounted project data outside the VHD is not included. No cloud upload is proposed.
3. **Preflight C: and D: capacity again.** Require the D: budget and C: startup headroom above.
   Any separate C: cleanup or application-data move needs its own precise approval. No broad
   disk sweep, temp deletion or Docker prune is included. No large build/pull/indexing runs.
4. **One controlled restart and supported relocation.** With the cold backup verified, launch
   Docker Desktop once. Inspect fresh logs and `docker version`. If Settings is accessible,
   use **Settings → Resources → Advanced → Disk image location**, select the new empty
   `D:\CodeAtlas\DockerDesktop` directory and let Desktop perform its supported relocation.
   Allow the Apply/restart it requests. Do not manually move VHD files, edit JSON/registry
   paths, import/unregister Docker distributions, switch image stores or replace an existing
   destination image. If the UI cannot relocate because the engine remains unhealthy, stop
   at the failure branch below; do not invent an offline path-edit workaround.
5. **Preservation checks before new workload.** Confirm the configured path and actual new
   host VHD on D:. Query server version, storage root, disk usage, and list *all* images,
   containers and volumes, including unrelated projects. Because the engine is currently
   unavailable, a reliable pre-recovery inventory cannot be captured now; the whole-disk cold
   backup is the preservation fallback. Save the first recovered inventory to D: before
   creating more resources. Keep existing Compose project names and named-volume mappings.
6. **Verify data, not just daemon liveness.** Check PostgreSQL recovery logs, migrations and
   important records; obtain logical DB backups and selected volume/image exports on D: once
   services are healthy. Image save alone does not preserve named-volume contents. Verify
   source decryption with the preserved key, grants and pinned snapshots; confirm other projects
   still see their images/volumes. Do not auto-run imported source/tests. Then resume the
   CodeAtlas Linux build, real-service tests and Phase 1 acceptance work within D: capacity.
7. **Retain backups and old-state evidence.** Do not delete the backup or manually clean up
   old disks. Desktop's supported migration may retire its old active copy as part of the
   approved move; the independently verified cold backup must remain. Keep enough temporary
   capacity until application-level restoration checks pass. Any later cleanup is a separate
   approval. Do not promise restoration of writes that already failed during disk exhaustion.

### Failure branch: engine still unhealthy after backup and headroom

- Stop after the one controlled attempt and read the new error. A stale failure state may clear
  after shutdown; persistent ext4 errors require a filesystem investigation before more writes.
- Prepare a separate working copy on D:, leaving the verified cold backup and original intact.
  Microsoft's supported WSL VHD repair workflow uses an elevated shell, a bare VHD attachment,
  device identification via lsblk, offline e2fsck and clean detach. Do not reuse the historical
  `/dev/sdf` name; devices must be identified afresh and proven unmounted. Starting a helper
  WSL distro itself needs approval and may write to its C: installation.
- Seek **separate approval** before any attachment/check/repair. A no-write offline check
  (`e2fsck -f -n` on the correctly identified unmounted working copy) can help characterize
  damage, but an unreplayed journal can affect findings. A repairing e2fsck modifies data and
  may discard unrecoverable metadata; it is not authorized by initial backup/relocation approval.
  Applying a repaired working copy to Docker also needs an explicitly approved Docker-supported
  restoration plan. Do not manually swap the live VHD as part of this procedure.
- If the filesystem becomes clean but containerd reports actual checksum/page/metadata damage,
  retain that evidence and escalate to Docker support with a reviewed, redacted diagnostic
  package. No automated upload is proposed. Do not delete Bolt metadata or reset the engine
  to make it start. Reinstall/reset/import/prune are outside this preservation-first approval.

## Documentation consulted

- [Docker Desktop whole-VM backup](https://docs.docker.com/desktop/settings-and-maintenance/backup-and-restore/):
  Docker must be stopped; WSL 2 backup uses docker_data.vhdx; named volumes need separate
  treatment when saving individual images.
- [Docker WSL 2 storage location](https://docs.docker.com/desktop/features/wsl/): supported
  relocation through Settings → Resources → Advanced.
- [Microsoft WSL VHD repair](https://learn.microsoft.com/en-us/windows/wsl/disk-space): offline
  VHD attachment, correct block-device identification, repair and detach. This is a conditional
  repair reference, not proof that Docker's data is corrupt or authorization to change it.

Approval requested: normal Docker quit/WSL shutdown, verified cold backup to the new D: backup
folder, one controlled restart after adequate headroom, and Desktop-managed relocation to D:.
This affects all Docker Desktop images/volumes. It excludes C: cleanup, filesystem repair,
manual VHD movement, resets, pruning, reinstalling and unrelated system settings. If capacity
or the supported UI prevents these steps, stop and present the specific next action.

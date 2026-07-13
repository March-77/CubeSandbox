# Real CubeSandbox cluster verification evidence

Verification dates: 2026-07-13 through 2026-07-14 (Asia/Shanghai)

Cluster:

- Tencent Cloud CVM SA9, 8 vCPU / 16 GiB
- OpenCloudOS 9.6, x86_64
- PVM host kernel `6.6.69-opencloudos9.cubesandbox.pvm.host-gb85200d80fa2`
- 200 GiB XFS data disk mounted at `/data/cubelet` with `reflink=1`
- CubeSandbox one-click deployment v0.5.1

This branch stores the screenshots and raw logs requested during review of
PRs #925, #926, and #928. It is intentionally separate from the PR branches so
verification artifacts do not enter the product diffs.

## PR #928

The source tree now identified by signed commit
`8cf007947cb4759f0da3c3f57bbd4a422f0ee6f7` was compiled on the cluster before
the DCO-only metadata rewrite.
All 85 Rust tests passed, the resulting binary was deployed to the one-click
CubeAPI service, and a real MicroVM lifecycle produced four HMAC-validated
webhooks: created, paused, resumed, and deleted.

## PR #926

The source tree now identified by signed commit
`7bd4f7b7d3d8d55f1f7133b4dbf9280fa340d59a` initially failed to build before
the DCO-only metadata rewrite because
Bundler 2.6.9 requires Ruby 3.1 while Ubuntu 22.04 supplies Ruby 3.0.2. After
pinning Bundler 2.5.23, the application then exposed a missing `rackup` runtime
dependency. Both fixes are included in signed follow-up commit `def4d7e`. The fixed
image was registered as a Cube template; `run_example.py` and
`resume_example.py` then passed in real MicroVMs.

Signed follow-up commit `9f10cc4` addresses the automated review's Medium findings:
the runtime image no longer contains build tools or curl, Sinatra runs as UID
1000 while the Cube `envd` process retains the privileges it requires, both
example scripts make executable response assertions, and pause/resume state is
verified through the Sinatra API. Template `tpl-5653d34da4ea4a4cbf9e21c5` reached
READY; the updated examples and an in-MicroVM process identity check all passed.

The refreshed automated review produced five follow-up findings. Commit
`5f0eda433ac7445c889fc603b32a5a84ec67d2a2` addresses them by retrying transient
non-JSON health responses, serializing counter updates with file locks,
initializing the data directory once, reporting cleanup failures, and clarifying
the runtime hardening intent. Replacement template
`tpl-36769b42f06641e3b3b39db1` reached READY. A real PVM MicroVM passed the
updated examples, strict TLS, process identity checks, and 20 concurrent counter
increments without lost updates.

## PR #925

The source tree now identified by signed commit
`02d932969274a7287421e0dca1890ec748221266` was used to build all three
Dockerfiles. Claude Code, CodeBuddy, and OpenCode images were registered as Cube
templates and booted as real PVM MicroVMs. CLI execution and pause/resume state
persistence passed for each template. No external model API call was made because
provider credentials were not part of the cluster-verification scope.

## DCO sign-off rewrite

The contributor later rebased the PR branches to add their personal DCO
`Signed-off-by` trailers. This changed commit IDs but not source trees. The
verified and signed commit pairs have identical Git tree IDs:

- PR #925: `c5f84f71` -> `02d93296`
- PR #926: `7be28fe4` -> `7bd4f7b7`, `96886cbf` -> `def4d7ea`,
  `97442160` -> `9f10cc4d`, `70f384c7` -> `5f0eda43`
- PR #928: `96ff2dfd` -> `8cf00794`

Raw logs retain the original pre-signoff commit IDs recorded at verification
time. Only commit metadata changed during sign-off; all corresponding tree IDs
were checked and match exactly.

## Network-only build accommodations

The server is in mainland China. The official CubeSandbox base manifest was
verified against a mirror by digest; Ubuntu, RubyGems, and Cargo transport
mirrors were used to avoid timeouts. Product versions and PR source behavior
were otherwise preserved. No credentials are included in these artifacts.

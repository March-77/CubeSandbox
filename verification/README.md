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

Commit `96ff2dfd7ae4e1b9036a84f2f9cec45915adaad4` was compiled on the cluster.
All 85 Rust tests passed, the resulting binary was deployed to the one-click
CubeAPI service, and a real MicroVM lifecycle produced four HMAC-validated
webhooks: created, paused, resumed, and deleted.

## PR #926

Commit `7be28fe4e7511f93438457b0b53c87f0ee1d0520` initially failed to build because
Bundler 2.6.9 requires Ruby 3.1 while Ubuntu 22.04 supplies Ruby 3.0.2. After
pinning Bundler 2.5.23, the application then exposed a missing `rackup` runtime
dependency. Both fixes are included in follow-up commit `96886cb`. The fixed
image was registered as a Cube template; `run_example.py` and
`resume_example.py` then passed in real MicroVMs.

Follow-up commit `9744216` addresses the automated review's Medium findings:
the runtime image no longer contains build tools or curl, Sinatra runs as UID
1000 while the Cube `envd` process retains the privileges it requires, both
example scripts make executable response assertions, and pause/resume state is
verified through the Sinatra API. Template `tpl-5653d34da4ea4a4cbf9e21c5` reached
READY; the updated examples and an in-MicroVM process identity check all passed.

The refreshed automated review produced five follow-up findings. Commit
`70f384c7d4277c5c89817717d07ca465e3d3d9a7` addresses them by retrying transient
non-JSON health responses, serializing counter updates with file locks,
initializing the data directory once, reporting cleanup failures, and clarifying
the runtime hardening intent. Replacement template
`tpl-36769b42f06641e3b3b39db1` reached READY. A real PVM MicroVM passed the
updated examples, strict TLS, process identity checks, and 20 concurrent counter
increments without lost updates.

## PR #925

Commit `c5f84f71c32df9c274812155e3bb77695c9808c2` was used to build all three
Dockerfiles. Claude Code, CodeBuddy, and OpenCode images were registered as Cube
templates and booted as real PVM MicroVMs. CLI execution and pause/resume state
persistence passed for each template. No external model API call was made because
provider credentials were not part of the cluster-verification scope.

## Network-only build accommodations

The server is in mainland China. The official CubeSandbox base manifest was
verified against a mirror by digest; Ubuntu, RubyGems, and Cargo transport
mirrors were used to avoid timeouts. Product versions and PR source behavior
were otherwise preserved. No credentials are included in these artifacts.

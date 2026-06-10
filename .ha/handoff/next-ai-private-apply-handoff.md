# Next AI Handoff: Private Cloud Apply

Repo: `/home/kt/project/hybrid-ai-serving-platform`
Branch: `feature/private`

## Goal

The user asked for the private-cloud provisioning changes to be fully validated
locally before any commit, push, or GitHub Actions apply.

Rules:

- Do not commit, push, or trigger GitHub Actions unless local validation is
  successful.
- If any validation fails, stop and report the failure.
- After successful local validation, commit, push to `origin/feature/private`,
  then trigger the GitHub Actions controller apply exactly once.
- After the Actions apply, confirm what resources and services are up.
- Keep the architecture and repeated operational rules documented under `.ha`.

## Requested Actions Structure

- Keep the private plan workflow.
- Consolidate private apply/destroy/platform/provision/registry/finalize into a
  controller-oriented workflow.
- Controller options:
  - `operation`: `apply` or `destroy`
  - `openstack_lifecycle`: `tenant-stack-only` or `full-openstack`
  - `validate_gpu`: boolean
- Keep mutex-sensitive phases serialized:
  - DevStack
  - image cache
  - Terraform
- Split VM provisioning into separate jobs so logs are separated by role:
  - control-plane
  - build-worker
  - gpu-worker
  - gitlab
  - harbor
- Run independent VM role jobs in parallel after Terraform.
- Consider phase locks and GitHub Actions concurrency so the same foundation is
  not mutated by overlapping runs.
- Reduce GitLab runtime I/O bottlenecks without changing the overall structure.

## Current Local State

OpenStack has five ACTIVE servers:

- `hybrid-ai-private-control-01`: `172.24.4.207`, private `10.42.0.146`
- `hybrid-ai-private-build-01`: `172.24.4.109`, private `10.42.0.232`
- `hybrid-ai-private-gpu-01`: `172.24.4.191`, private `10.42.0.154`
- `hybrid-ai-private-gitlab-01`: `172.24.4.239`, private `10.42.0.143`
- `hybrid-ai-private-harbor-01`: `172.24.4.130`, private `10.42.0.116`

Terraform apply path was verified as no-op:

- `0 added`
- `0 changed`
- `0 destroyed`

GitLab:

- `https://gitlab.intp.me/users/sign_in` returned HTTP `200`.
- `sidekiq` is running inside the GitLab container.
- Runtime I/O mitigations are applied:
  - `/tmp` tmpfs
  - Docker local log driver with size/file limits
  - container blkio weight `300`
  - Rails tmpfs disabled by default
- A GitLab reapply completed without container recreation in about `89s`.

Harbor:

- `https://harbor.intp.me/api/v2.0/ping` returned HTTP `200`.
- Harbor containers are healthy.

OpenStack Kubernetes:

- Use `.ha/openstack/kubeconfig`, not `.ha/kubeconfig`.
- The kubeconfig expects a local tunnel:
  - `127.0.0.1:16443` -> control node `127.0.0.1:6443`
- Verified:
  - three nodes Ready
  - Argo Running
  - MinIO Running
  - NFS provisioner Running
  - kube-system pods Running

Static checks passed before the final GPU follow-up:

- `bash -n`
- `git diff --check`
- `actionlint`
- `terraform -chdir=private/openstack fmt -check main.tf variables.tf outputs.tf`

## Important Remaining Issue

The GPU VM is the last incomplete validation item.

Original problem:

- The VM originally booted with CUDA Toolkit `12.1` and PyTorch `cu121`.
- The GPU is RTX 5060 Ti and requires support for `sm_120`.
- PyTorch `cu121` failed with:
  - `CUDA error: no kernel image is available for execution on the device`

Code was patched to use:

- CUDA Toolkit package: `cuda-toolkit-12-8`
- PyTorch index: `https://download.pytorch.org/whl/cu128`
- PyTorch packages:
  - `torch==2.7.0+cu128`
  - `torchvision==0.22.0+cu128`
  - `torchaudio==2.7.0+cu128`

The current GPU VM venv was manually upgraded to PyTorch `2.7.0+cu128`, and a
CUDA tensor test succeeded.

Resolution (2026-06-10):

- The interrupted apt install was resumed; `cuda-toolkit-12-8` and
  `cudnn9-cuda-12` are fully installed (`dpkg --audit` clean).
- `update-alternatives` now points `/usr/local/cuda` at `cuda-12.8`.
- `/usr/local/bin/nvcc` symlink and `/etc/profile.d/hybrid-ai-cuda.sh` were
  created on the existing VM, matching what the patched cloud-init bootstrap
  does on a fresh boot.
- `nvcc --version` reports `12.8`, `sudo /usr/local/sbin/hybrid-ai-dependency-check`
  exits `0`, and the PyTorch CUDA tensor test passes with `sm_120` in the arch
  list.
- The `gpu-worker` phase (`./ha apply --run-mode apply --phases gpu-worker`)
  completed `OK`. The VM still has a historical `cloud-final.service` failed
  unit from the original cu121 boot; the phase tolerates it because the GPU
  runtime dependency check passes. A freshly provisioned VM with the patched
  template will not hit this.

## Continue From Here

First verify GPU state:

```bash
ssh -F .ha/openstack/ssh_config 172.24.4.191 'nvcc --version'
ssh -F .ha/openstack/ssh_config 172.24.4.191 'sudo /usr/local/sbin/hybrid-ai-dependency-check'
```

Run a PyTorch CUDA tensor check on the GPU VM:

```bash
ssh -F .ha/openstack/ssh_config 172.24.4.191 '/opt/hybrid-ai/training-venv/bin/python - <<'"'"'PY'"'"'
import torch
print("torch_version=", torch.__version__)
print("torch_cuda_version=", torch.version.cuda)
print("cuda_available=", torch.cuda.is_available())
print("device_count=", torch.cuda.device_count())
print("arch_list=", torch.cuda.get_arch_list())
x = torch.ones((2, 2), device="cuda")
print("cuda_tensor=", x * 2)
PY'
```

Then verify the same local phase path that GitHub Actions uses:

```bash
TF_BACKEND_TYPE=local \
TF_BACKEND_CONFIG='path="/home/kt/project/hybrid-ai-serving-platform/.ha/tfstate/private-cloud-foundation.tfstate"' \
./ha apply --run-mode apply --phases gpu-worker --require-backend-config
```

Re-run static validation:

```bash
bash -n ha private/ci/private-cloud-apply.sh private/ci/private-cloud-destroy.sh private/openstack/scripts/cache-openstack-images.sh private/openstack/scripts/hybrid-ai-gitlab-bootstrap private/openstack/scripts/hybrid-ai-harbor-bootstrap
git diff --check
actionlint .github/workflows/private-cloud-controller.yml .github/workflows/private-cloud-remote.yml .github/workflows/private-cloud-plan.yml
terraform -chdir=private/openstack fmt -check main.tf variables.tf outputs.tf
```

Reconfirm Terraform remains no-op:

```bash
TF_BACKEND_TYPE=local \
TF_BACKEND_CONFIG='path="/home/kt/project/hybrid-ai-serving-platform/.ha/tfstate/private-cloud-foundation.tfstate"' \
./ha apply --run-mode apply --phases terraform --require-backend-config
```

## Commit And Push Only If All Validation Passes

If every local validation passes:

```bash
git add .github/workflows/private-cloud-controller.yml
git add .github/workflows/private-cloud-remote.yml
git add .github/workflows/private-cloud-plan.yml
git add .github/workflows/private-cloud-apply.yml
git add .github/workflows/private-cloud-destroy.yml
git add .github/workflows/private-cloud-finalize.yml
git add .github/workflows/private-cloud-platform.yml
git add .github/workflows/private-cloud-provision.yml
git add .github/workflows/private-cloud-registry.yml
git add README.md ha
git add private/ci/private-cloud-apply.sh private/ci/private-cloud-destroy.sh
git add private/handoff/github-actions-env.md
git add private/openstack/cloud-init/base.yaml.tftpl
git add private/openstack/scripts/cache-openstack-images.sh
git add private/openstack/scripts/hybrid-ai-gitlab-bootstrap
git add private/openstack/scripts/hybrid-ai-harbor-bootstrap
git add private/openstack/terraform.tfvars.example
git add private/openstack/variables.tf
git add -f .ha/private-cloud-actions-architecture.md
git add -f .ha/handoff/next-ai-private-apply-handoff.md
git commit -m "Consolidate private cloud controller workflow"
git push origin feature/private
```

After push, trigger exactly one controller apply:

```bash
gh workflow run private-cloud-controller.yml \
  --ref feature/private \
  -f operation=apply \
  -f openstack_lifecycle=tenant-stack-only \
  -f validate_gpu=false
```

Then monitor the run and confirm resulting infrastructure and service state.

## Do Not Continue If

- GPU dependency check fails.
- `gpu-worker` phase fails.
- Terraform is not no-op unless the user explicitly accepts the planned change.
- GitLab or Harbor health checks fail.
- OpenStack Kubernetes nodes or platform pods are not Ready/Running.
- Static validation fails.

In any of those cases, do not commit, do not push, and do not trigger GitHub
Actions.

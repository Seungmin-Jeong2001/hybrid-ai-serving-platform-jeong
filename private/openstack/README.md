# OpenStack 프로비저닝

이 디렉터리는 Private Cloud Foundation의 OpenStack 자원을 Terraform으로
프로비저닝하기 위한 작업 영역입니다. 현재 단계에서는 실제 운영값을 넣지 않고,
GitHub Actions에서 plan/apply까지 연결할 수 있는 기본 골격을 관리합니다.

## 작업 범위

- private network와 subnet을 생성합니다.
- external network ID가 주어지면 router gateway까지 연결합니다.
- floating IP pool이 주어지면 node bootstrap용 floating IP를 할당합니다.
- SSH 접근과 내부 east-west 통신을 위한 기본 security group을 생성합니다.
- control-plane, build-worker, GPU-worker, standalone GitLab VM 그룹을 역할별로 나눠 생성합니다.
- Kubernetes bootstrap에서 사용할 node inventory를 output으로 남깁니다.
- cloud-init으로 Kubernetes, storage, diagnostics, GPU worker host dependency를 설치합니다.
- GPU worker는 NVIDIA Container Toolkit, driver autoinstall, PCIe performance policy, link/throughput 진단 스크립트를 준비합니다.
- GitLab VM은 Kubernetes node inventory에 포함하지 않습니다. Apply workflow가 GitLab CE package를 설치하고
  `gitlab.intp.me` Caddy upstream으로 연결합니다.

## 입력값 관리

OpenStack 인증 정보는 표준 `OS_*` 환경 변수나 GitHub Actions Secret으로만
주입합니다. `clouds.yaml`, `openrc`, kubeconfig, token, password, 내부 endpoint는
repository에 커밋하지 않습니다.

로컬 검증에서는 먼저 `ha up openstack-local --auto-approve`로 DevStack을 올립니다.
그 다음 생성된 `.ha/openstack-local/openrc.sh`를 source 하면 Terraform이 사용할
`OS_AUTH_URL`, project, user credential이 현재 shell로 전달됩니다.

외부/운영 OpenStack을 사용할 때의 `OS_AUTH_URL`은 이 repository가 생성하는 값이 아니라,
이미 존재하는 Keystone/Identity endpoint입니다.

최소 필요 값:

- `OS_AUTH_URL`
- `OS_USERNAME`
- `OS_PASSWORD`
- `OS_PROJECT_NAME`
- `OS_USER_DOMAIN_NAME`
- `OS_PROJECT_DOMAIN_NAME`
- `TF_VAR_ssh_public_key`

## 로컬 점검

```sh
ha test
ha test --integration
```

실제 OpenStack 리소스를 올릴 때는 repository root에서 실행합니다.

```sh
ha up openstack --auto-approve
```

로컬 DevStack smoke apply는 `cirros` 이미지와 작은 flavor로 실행합니다. 이 검증은
network/subnet/router/security group/key pair/VM 생성 확인용입니다. Kubernetes node로
쓸 production 검증은 Ubuntu 계열 cloud image와 충분한 flavor를 사용해야 합니다.

OpenStack VM을 Kubernetes node로 bootstrap하려면 Ubuntu 계열 image와 floating IP 또는
private network SSH 경로를 준비한 뒤 실행합니다.

```sh
ha up openstack-kubernetes --auto-approve
```

로컬에서 확인할 때만 `terraform.tfvars.example`을 `terraform.tfvars`로 복사해서
사용합니다. 값이 채워진 `terraform.tfvars`, Terraform state, backend 설정 파일은 커밋하지 않습니다.

## OpenStack provider v3 migration

OpenStack provider v3에서는 Nova compute floating IP association resource가 제거되었습니다.
이 구성은 Neutron `openstack_networking_floatingip_v2`의 `port_id`로 floating IP를 연결합니다.

기존 state가 `openstack_compute_floatingip_associate_v2`를 이미 추적하고 있으면 provider v3가
해당 schema를 읽을 수 없어 plan이 실패합니다. state를 백업한 뒤, 실제 floating IP는 유지하고
Terraform 추적 항목만 제거합니다.

```sh
ha tf state list | rg openstack_compute_floatingip_associate_v2
ha tf state rm 'openstack_compute_floatingip_associate_v2.control_plane[0]'
```

build-worker 또는 GPU-worker association이 state에 있으면 같은 방식으로 해당 주소를 제거한 뒤
다시 plan을 확인합니다.

## Node dependency bootstrap

Terraform으로 생성되는 VM은 cloud-init 단계에서 아래 host dependency를 자동 설치합니다.

- Kubernetes host prereq: `overlay`, `br_netfilter`, bridge sysctl, IP forwarding
- Storage prereq: `nfs-common`, `open-iscsi`, `multipath-tools`, `nvme-cli`, `xfsprogs`
- Diagnostics/build tools: `build-essential`, `git`, `jq`, `pciutils`, `lshw`, `hwloc`, `numactl`, `fio`, `sysstat`
- Guest integration: `qemu-guest-agent`
- GPU worker prereq: NVIDIA Container Toolkit repo/package, `ubuntu-drivers autoinstall`, `nvidia-persistenced`
- GPU CUDA base: NVIDIA CUDA Toolkit and cuDNN apt packages, default `cuda-toolkit-12-1` and `cudnn9-cuda-12`
- GPU PCIe tuning: PCIe ASPM `performance` policy, CPU governor `performance`, `nvidia-smi` PCIe link/counter report
- GPU training prereq: `/opt/hybrid-ai/training-venv` Python venv with the `feature/model` training stack:
  PyTorch CUDA 12.1 wheels, NumPy, Pandas, SciPy, scikit-learn, Matplotlib, Seaborn, Notebook/IPython kernel,
  and MinIO client. The helper commands `hybrid-ai-training-python`, `hybrid-ai-training-pip`,
  `hybrid-ai-training-jupyter`, and `hybrid-ai-training-notebook` point at this venv when available.
- GitLab shell training helper: `hybrid-ai-training-run`, which creates a per-job venv and installs the repo
  `requirements.txt` at training time.

The GPU training venv is controlled by these Terraform variables:

```hcl
enable_gpu_cuda_bootstrap           = true
gpu_cuda_toolkit_package            = "cuda-toolkit-12-1"
gpu_cudnn_package                   = "cudnn9-cuda-12"
enable_gpu_training_bootstrap       = true
gpu_training_venv_path              = "/opt/hybrid-ai/training-venv"
gpu_training_pytorch_cuda_index_url = "https://download.pytorch.org/whl/cu121"
gpu_training_pip_cache_dir          = "/mnt/nfs/hybrid-ai/pip-cache"
gpu_training_python_packages = [
  "torch==2.1.0+cu121",
  "torchvision==0.16.0+cu121",
  "torchaudio==2.1.0+cu121",
  "numpy==1.26.4",
  "pandas==2.2.2",
  "scipy==1.11.4",
  "scikit-learn==1.4.2",
  "matplotlib==3.8.4",
  "seaborn==0.13.2",
  "notebook==7.2.2",
  "ipykernel==6.29.5",
  "minio==7.2.8",
]
```

When `enable_gpu_training_bootstrap=true`, `hybrid-ai-dependency-check` also runs
`hybrid-ai-gpu-training-check`, which imports the training modules and executes a small CUDA tensor operation
through PyTorch.

For GitLab CI shell jobs, keep project-specific dependencies and the training entrypoint in the model repo:

```txt
requirements.txt
train.py
```

The GitLab job should call `hybrid-ai-training-run` with the command for that repository:

```sh
hybrid-ai-training-run \
  --requirements requirements.txt \
  -- python train.py
```

This installs `requirements.txt` during the training job when the file exists instead of baking every
project dependency into the GPU VM image.

## Local DevStack GPU passthrough

Local DevStack mode configures Nova PCI passthrough for the first detected NVIDIA display/3D PCI device.
It creates or updates a dedicated GPU flavor, default `g1.large`, with `pci_passthrough:alias=nvidia-gpu:1`.
Keep `GPU_WORKER_FLAVOR_NAME` separate from `BUILD_WORKER_FLAVOR_NAME`; sharing `m1.large` would make normal
build workers request the GPU too.

Default local GPU passthrough values:

- PCI vendor ID: `10de`
- PCI product ID: auto-detected from `/sys/bus/pci/devices`
- Nova PCI device type: `type-PF`. The same value is written to `device_spec` as `dev_type` so `PciPassthroughFilter`
  can match the physical function pool.
- Nova alias: `nvidia-gpu`
- GPU flavor: `g1.large`, `8192` MiB RAM, `4` vCPU, `40` GiB disk
- Host VFIO bind: enabled by default. The GPU's full IOMMU group is bound to `vfio-pci` so companion
  functions, such as NVIDIA HDMI audio, do not keep the group non-viable.

Override only when the hardware or desired local flavor shape differs:

```sh
HA_OPENSTACK_GPU_PCI_PRODUCT_ID=2d04 \
HA_OPENSTACK_GPU_BIND_IOMMU_GROUP=true \
HA_OPENSTACK_GPU_FLAVOR_NAME=g1.large \
ha up openstack-local --auto-approve
```

GPU PCIe lane width/generation 자체는 BIOS, hypervisor, physical slot, passthrough/vGPU 설정의 영향을 받습니다.
VM 안에서는 가능한 guest-side performance policy와 진단까지만 자동화합니다.
Actual VM passthrough still requires host IOMMU support and a GPU that can be detached from host display/audio
use. Set `HA_OPENSTACK_GPU_BIND_IOMMU_GROUP=false` only when the host already prepares a viable VFIO group
through another mechanism.

노드 내부 검증:

```sh
sudo /usr/local/sbin/hybrid-ai-dependency-check
sudo /usr/local/sbin/hybrid-ai-gpu-pcie-tune
sudo /usr/local/sbin/hybrid-ai-gpu-training-check
```

## Storage access from standalone VMs

NFS는 첫 control-plane VM에서 export되고, export CIDR은 Terraform의 `private_network_cidr`입니다.
security group도 같은 CIDR의 내부 TCP/UDP/ICMP를 허용하므로 GPU worker와 GitLab VM처럼 같은 private network에
붙은 VM은 NFS server private IP로 접근할 수 있습니다.

MinIO는 Kubernetes 안의 tenant로 설치됩니다. Pod에서는
`http://minio-api.minio-tenant.svc.cluster.local:9000`로 접근하고, Kubernetes 밖의 standalone VM은
같은 private network에 있는 Kubernetes node IP의 NodePort로 접근합니다.

- MinIO API: `http://<k8s-node-private-ip>:30900`
- MinIO console: `http://<k8s-node-private-ip>:30990`

GitLab VM이 같은 OpenStack private network에 붙어 있으므로 security group 기준으로 이 NodePort 접근이 허용됩니다.

GitLab web UI는 Caddy reverse proxy가 VM port 80으로 붙을 때만 직접 HTTP가 필요합니다. 기본 Terraform 값은
`gitlab_http_allowed_cidrs = []`이고, local DevStack Apply workflow는 DevStack public subnet CIDR만 자동으로
허용해서 `127.0.0.1:18083` upstream을 GitLab VM floating IP port 80으로 연결합니다.

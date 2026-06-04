# GitHub Actions Environment Mapping

이 문서는 로컬 `.env`, `.env.secret` 값을 GitHub Actions로 옮길 때의 기준입니다.
공개 가능한 설정값은 GitHub Variables, credential과 token은 GitHub Secrets에 둡니다.

## Private Cloud Foundation workflows

Workflows:

- `.github/workflows/private-cloud-plan.yml`: user-facing plan workflow
- `.github/workflows/private-cloud-apply.yml`: user-facing apply workflow
- `.github/workflows/private-cloud-destroy.yml`: user-facing destroy workflow
- `.github/workflows/private-cloud-foundation.yml`: reusable core called by the three workflows

### GitHub Secrets

| Secret | 로컬 값 | 용도 |
| --- | --- | --- |
| `OPENSTACK_PASSWORD` | `OS_PASSWORD` | OpenStack password |
| `PRIVATE_CLOUD_SSH_PUBLIC_KEY` | `TF_VAR_ssh_public_key` | VM SSH keypair public key |
| `TF_BACKEND_CONFIG` | `TF_BACKEND_CONFIG` | plan/apply/destroy용 Terraform remote state |
| `PRIVATE_CLOUD_TFVARS` | `*.auto.tfvars` 내용 | CIDR, node count 등 환경별 Terraform override |

`install_openstack=true`로 Actions가 로컬 DevStack을 만들 때는 `OPENSTACK_PASSWORD`가 DevStack
`admin` password가 됩니다. 이 값은 DevStack config와 여러 service URL에 들어가므로 workflow가
다음 DevStack-safe policy를 먼저 검사합니다: 8-128자, whitespace 없음, 허용 문자 `A-Z a-z 0-9 . _ ~ ! -`.
이미 떠 있는 DevStack container는 Secret 변경만으로 password가 바뀌지 않으므로, known password로 다시
맞추려면 `force_cleanup=true`로 재설치합니다.

### GitHub Variables

| Variable | 로컬 값 | 용도 |
| --- | --- | --- |
| `OPENSTACK_AUTH_URL` | `OS_AUTH_URL` | OpenStack Keystone endpoint |
| `OPENSTACK_USERNAME` | `OS_USERNAME` | OpenStack user |
| `OPENSTACK_PROJECT_NAME` | `OS_PROJECT_NAME` | OpenStack project |
| `OPENSTACK_USER_DOMAIN_NAME` | `OS_USER_DOMAIN_NAME` | OpenStack user domain, 기본 `Default` |
| `OPENSTACK_PROJECT_DOMAIN_NAME` | `OS_PROJECT_DOMAIN_NAME` | OpenStack project domain, 기본 `Default` |
| `OPENSTACK_REGION` | `OS_REGION_NAME` | OpenStack region |
| `CONTROL_PLANE_IMAGE_NAME` | `TF_VAR_control_plane_image_name` | control-plane VM image |
| `CONTROL_PLANE_FLAVOR_NAME` | `TF_VAR_control_plane_flavor_name` | control-plane VM flavor |
| `BUILD_WORKER_IMAGE_NAME` | `TF_VAR_build_worker_image_name` | build worker VM image |
| `BUILD_WORKER_FLAVOR_NAME` | `TF_VAR_build_worker_flavor_name` | build worker VM flavor |
| `GPU_WORKER_IMAGE_NAME` | `TF_VAR_gpu_worker_image_name` | GPU worker VM image |
| `GPU_WORKER_FLAVOR_NAME` | `TF_VAR_gpu_worker_flavor_name` | GPU worker VM flavor |
| `PRIVATE_CLOUD_RUNNER` | self-hosted runner label | Private OpenStack endpoint에 접근할 runner |
| `TF_BACKEND_TYPE` | `TF_BACKEND_TYPE` | Terraform backend type, self-hosted local 검증은 `local` |
| `PRIVATE_CLOUD_SSH_USER` | bootstrap SSH user | dependency bootstrap 검증용 SSH user |
| `PRIVATE_CLOUD_K8S_VERSION_MINOR` | `HA_K8S_VERSION_MINOR` | Kubernetes apt repository minor, 기본 `v1.36` |
| `PRIVATE_CLOUD_K8S_POD_CIDR` | `HA_K8S_POD_CIDR` | kubeadm과 CNI가 사용할 Pod CIDR, 기본 `192.168.0.0/16` |
| `PRIVATE_CLOUD_K8S_CNI_MANIFEST` | `HA_K8S_CNI_MANIFEST` | bootstrap 후 적용할 CNI manifest, 기본 Calico |
| `PRIVATE_CLOUD_K8S_API_ENDPOINT` | `HA_K8S_API_ENDPOINT` | kubeconfig에 기록할 API endpoint, 기본 `PRIVATE_CLOUD_TAILSCALE_IP` |

### Optional GitHub Secrets

| Secret | 로컬 값 | 용도 |
| --- | --- | --- |
| `PRIVATE_CLOUD_SSH_PRIVATE_KEY` | OpenStack VM SSH private key | cloud-init 완료, dependency check, Kubernetes bootstrap을 Actions에서 검증 |
| `PRIVATE_CLOUD_KUBECONFIG_B64` | `base64 < kubeconfig` | `destroy` 전 Kubernetes resource cleanup이 필요할 때 사용할 kubeconfig |

`feature/private` push 실행은 `Private Cloud Plan`만 자동 실행하며 Terraform `plan`과 DNS dry-run까지만 수행합니다.
OpenStack 리소스와 Cloudflare DNS를 실제로 바꾸는 `Private Cloud Apply`와 `Private Cloud Destroy`는 수동으로 실행합니다.

Private OpenStack API가 Tailscale 또는 로컬 네트워크 안에 있으면 GitHub-hosted runner에서
접근할 수 없습니다. Foundation workflow는 기본적으로 repository self-hosted runner에서 실행합니다.
runner가 여러 대이면 `PRIVATE_CLOUD_RUNNER`에 더 구체적인 label을 지정합니다.

### 수동 CD 실행 순서

1. `Private Cloud Plan`으로 변경 내용을 먼저 확인합니다.
2. 문제가 없으면 `Private Cloud Apply`를 실행합니다. Kubernetes bootstrap과 baseline manifest apply는 고정으로 실행됩니다.
3. Storage 설치는 `setup_storage=true`, GPU 검증은 `validate_gpu=true`를 실제 backing 준비 후 선택합니다.
4. 제거는 `Private Cloud Destroy`로 실행합니다. Kubernetes 사전 cleanup이 필요하면 `PRIVATE_CLOUD_KUBECONFIG_B64`를 넣습니다.
5. DNS는 각 workflow와 한몸으로 움직입니다. Plan은 dry-run, Apply는 upsert, Destroy는 delete입니다.

`bootstrap_kubernetes=true`는 `action=apply`와 `PRIVATE_CLOUD_SSH_PRIVATE_KEY`가 필요합니다.
bootstrap 이후 workflow가 kubeconfig artifact를 만들고, `apply_kubernetes=true`이면 baseline manifest를 적용합니다.
`setup_storage=true`는 같은 SSH key로 첫 control-plane에 NFS export를 준비한 뒤 MinIO와 NFS provisioner를 설치합니다.

### OpenStack 계정 구분

외부 OpenStack 로그인은 `OPENSTACK_USERNAME`/`OPENSTACK_PASSWORD`와 project/domain Variables에서만 옵니다.
workflow에는 이 값들의 기본 계정이 없습니다.

로컬 DevStack을 설치할 때 보이는 `stack`은 DevStack 실행용 Linux 사용자이고, `admin`은 DevStack이 만드는
로컬 OpenStack 관리자 계정입니다. 둘 다 외부 OpenStack provider 계정 기본값이 아닙니다.

## Private Cloud DNS

DNS는 Plan/Apply/Destroy workflow 안에서 자동 실행됩니다.

### GitHub Secrets

| Secret | 로컬 값 | 용도 |
| --- | --- | --- |
| `CLOUDFLARE_API_TOKEN` | `CLOUDFLARE_API_TOKEN` | DNS record upsert와 Caddy DNS-01 인증서 발급 |

### GitHub Variables

| Variable | 로컬 값 | 용도 |
| --- | --- | --- |
| `CLOUDFLARE_ZONE_ID` | `CLOUDFLARE_ZONE_ID` | `intp.me` Cloudflare zone ID |
| `PRIVATE_CLOUD_BASE_DOMAIN` | `HA_BASE_DOMAIN` | 기본 domain, 예: `intp.me` |
| `PRIVATE_CLOUD_TAILSCALE_IP` | `HA_TAILSCALE_IP` | 물리 서버 Tailscale IPv4 |
| `PRIVATE_CLOUD_DNS_TTL` | `HA_CLOUDFLARE_DNS_TTL` | DNS TTL, 기본 `120` |
| `PRIVATE_CLOUD_DNS_SERVICES` | `HA_DNS_SERVICES` | CNAME 대상 서비스 목록, 기본 `openstack,k8s,grafana,argocd` |

## GitHub Actions로 옮기지 않는 값

아래 값은 로컬 실행 편의값이라 GitHub Actions에 넣을 필요가 없습니다.

| 값 | 이유 |
| --- | --- |
| `HA_PROVIDER` | workflow별로 provider가 고정되어 있음 |
| `HA_LOCAL_KUBECONFIG` | 로컬 파일 경로 |
| `HA_OPENSTACK_KUBECONFIG` | 로컬 파일 경로 |
| `HA_LXD_CONTAINER` | 로컬 LXD container 이름 |
| `HA_OPENSTACK_CONTAINER` | 로컬 DevStack container 이름 |
| `HA_DEVSTACK_BRANCH` | 로컬 DevStack 검증용 |
| `HA_DEVSTACK_PASSWORD` | 로컬 DevStack 검증용 password |
| `HA_OPENSTACK_HORIZON_UPSTREAM` | Caddy runtime에서만 필요 |
| `HA_K8S_DASHBOARD_UPSTREAM` | Caddy runtime에서만 필요 |
| `HA_GRAFANA_UPSTREAM` | Caddy runtime에서만 필요 |
| `HA_ARGOCD_UPSTREAM` | Caddy runtime에서만 필요 |

# OpenStack 프로비저닝

이 디렉터리는 Private Cloud Foundation의 OpenStack 자원을 Terraform으로
프로비저닝하기 위한 작업 영역입니다. 현재 단계에서는 실제 운영값을 넣지 않고,
GitHub Actions에서 plan/apply까지 연결할 수 있는 기본 골격을 관리합니다.

## 작업 범위

- private network와 subnet을 생성합니다.
- external network ID가 주어지면 router gateway까지 연결합니다.
- SSH 접근과 내부 east-west 통신을 위한 기본 security group을 생성합니다.
- control-plane, build-worker, GPU-worker VM 그룹을 역할별로 나눠 생성합니다.
- Kubernetes bootstrap에서 사용할 node inventory를 output으로 남깁니다.

## 입력값 관리

OpenStack 인증 정보는 표준 `OS_*` 환경 변수나 GitHub Actions Secret으로만
주입합니다. `clouds.yaml`, `openrc`, kubeconfig, token, password, 내부 endpoint는
repository에 커밋하지 않습니다.

최소 필요 값:

- `OS_AUTH_URL`: 이 repository가 생성하는 값이 아니라, 이미 존재하는 OpenStack Keystone/Identity endpoint입니다.
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

로컬에서 확인할 때만 `terraform.tfvars.example`을 `terraform.tfvars`로 복사해서
사용합니다. 값이 채워진 `terraform.tfvars`, Terraform state, backend 설정 파일은 커밋하지 않습니다.

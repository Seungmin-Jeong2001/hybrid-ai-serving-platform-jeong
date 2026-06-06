# Local OpenStack Control Plane

이 디렉터리는 외부 OpenStack tenant가 없을 때, 로컬 LXD 컨테이너 안에 DevStack 기반
OpenStack control plane을 올리는 bootstrap 스크립트를 제공합니다.

이 단계가 성공하면 이후 `private/openstack` Terraform은 생성된 OpenStack API에
붙어서 network, subnet, security group, key pair, VM node group을 만들 수 있습니다.

## 실행

권장 진입점은 repository root의 `ha` CLI입니다.

```sh
./ha up openstack-local --auto-approve
```

스크립트를 직접 실행할 수도 있습니다.

```sh
private/openstack-local/bootstrap-devstack.sh
```

기본값:

- LXD 컨테이너: `ha-openstack`
- 이미지: `ubuntu:24.04`
- DevStack branch: `master`
- 로컬 admin password: `hybrid-ai-devstack`
- GPU passthrough alias/flavor: `nvidia-gpu`, `g1.large`
- GPU passthrough VFIO bind: GPU IOMMU group 전체를 `vfio-pci`로 bind

환경 변수로 조정할 수 있습니다.

```sh
HA_OPENSTACK_CONTAINER=ha-openstack \
HA_OPENSTACK_LXD_IMAGE=ubuntu:24.04 \
HA_DEVSTACK_BRANCH=master \
HA_DEVSTACK_PASSWORD=hybrid-ai-devstack \
HA_OPENSTACK_GPU_PCI_PRODUCT_ID=auto \
HA_OPENSTACK_GPU_BIND_IOMMU_GROUP=true \
HA_OPENSTACK_GPU_FLAVOR_NAME=g1.large \
private/openstack-local/bootstrap-devstack.sh
```

## 호스트 요구사항

- LXD가 실행 중이어야 합니다.
- DevStack이 Open vSwitch/OVN을 사용하므로 호스트 커널에 `openvswitch`,
  `vport-geneve`, `vport-vxlan` 모듈이 있어야 합니다.
- Ubuntu 계열 호스트에서 모듈이 없으면 보통 `linux-modules-extra-$(uname -r)`
  패키지를 설치해야 합니다.
- GPU passthrough를 검증하려면 host BIOS/OS에서 IOMMU가 켜져 있어야 하고,
  `/dev/vfio`가 host와 LXD container 양쪽에서 보여야 합니다.
- 기본값은 GPU와 companion audio function이 같은 IOMMU group에 있는 경우까지 처리하기 위해
  전체 group을 `vfio-pci`로 bind합니다. Host가 해당 GPU를 display/audio 용도로 사용 중이면
  `HA_OPENSTACK_GPU_BIND_IOMMU_GROUP=false`로 끄고 별도 passthrough 준비를 먼저 해야 합니다.

## 결과 파일

성공하면 아래 파일이 생성됩니다.

```txt
.ha/openstack-local/openrc.sh
.ha/handoff/local-openstack.env
```

Terraform/OpenStack CLI를 사용할 때는 다음처럼 로드합니다.

```sh
source .ha/openstack-local/openrc.sh
```

로컬 DevStack이 준비된 뒤 Terraform으로 최소 프로비저닝을 검증할 수 있습니다.

```sh
source .ha/openstack-local/openrc.sh
export HA_PROVIDER=openstack
export TF_VAR_project_name=hybrid-ai-dev
export TF_VAR_external_network_id="$(lxc exec "${HA_OPENSTACK_CONTAINER:-ha-openstack}" -- sudo -u stack -H bash -lc 'cd /opt/stack/devstack && source openrc admin admin && openstack network show public -f value -c id')"
export TF_VAR_private_network_cidr=10.44.0.0/24
export TF_VAR_control_plane_count=1
export TF_VAR_build_worker_count=0
export TF_VAR_gpu_worker_count=0
export TF_VAR_control_plane_image_name=cirros-0.6.3-x86_64-disk
export TF_VAR_control_plane_flavor_name=m1.tiny
./ha up openstack --auto-approve
```

## 주의

DevStack은 개발/검증용 OpenStack입니다. production OpenStack 배포에는 Kolla-Ansible,
Canonical OpenStack/Sunbeam, OpenStack-Ansible 같은 별도 배포 방식을 사용해야 합니다.

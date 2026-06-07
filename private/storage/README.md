# Storage 기본 리소스

이 디렉터리는 Private Kubernetes에서 model build cache와 model artifact를 다루기 위한
storage 기본 리소스를 관리합니다. 현재는 NFS CSI 기반 RWX StorageClass와 PVC 예시를
먼저 잡아 둔 상태입니다.

## 적용 순서

GitHub Actions `Private Cloud Apply`의 `setup_storage=true`가 아래 항목을 순서대로 설치합니다.

- local-path provisioner
- MinIO Operator와 MinIO tenant
- NFS server export와 nfs-subdir-external-provisioner
- shared PVCs

PVC manifest만 수동으로 다시 적용할 때는 다음 명령을 사용합니다.

```sh
kubectl apply -k private/storage
```

적용 전 확인할 것:

- `storageclasses.yaml`의 NFS server/share 값은 실제 환경에서만 치환합니다.
- MinIO와 NFS provisioner Helm values는 GitHub Actions workflow에서 관리합니다.
- access key, secret key, 내부 endpoint, bucket credential은 커밋하지 않습니다.

MinIO tenant는 기본적으로 private network VM에서도 접근할 수 있도록 고정 NodePort를 사용합니다.
기본 tenant shape은 단일 서버에 4개 local-path volume을 붙이고, GitHub Actions 기본값은
volume당 `10Gi`입니다. 따라서 기본 요청량은 총 `40Gi`입니다.

- API: `http://<k8s-node-private-ip>:30900`
- Console: `http://<k8s-node-private-ip>:30990`

Pod 내부에서는 기존 cluster DNS인 `http://minio-api.minio-tenant.svc.cluster.local:9000`를 사용합니다.

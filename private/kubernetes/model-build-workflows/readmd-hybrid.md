7. 신규 Secret 필요: gitlab-ecr-trigger

trigger-gitlab-ecr-sync에서 아래 Secret을 사용합니다.

namespace: model-build
secret name: gitlab-ecr-trigger
keys:
  - token
  - projectId

생성 예시는 다음입니다.

kubectl -n model-build create secret generic gitlab-ecr-trigger \
  --from-literal=token='<GITLAB_TRIGGER_TOKEN>' \
  --from-literal=projectId='<GITLAB_PROJECT_ID>'

projectId는 GitLab project의 숫자 ID를 추천합니다.
예를 들어 GitLab URL이 아래처럼 되는 프로젝트입니다.

https://gitlab.intp.me/api/v4/projects/<projectId>/trigger/pipeline


```bash
MinIO datasets/raw-data/v1.0.4/_SUCCESS 업로드
→ argo-events/minio-eventsource 감지
→ argo-events/minio-sensor 실행
→ model-build namespace에 Workflow 생성
→ model-build-job WorkflowTemplate 실행
→ GPU node에서 model_build.py 실행
→ prepare-files에서 GitLab repo clone + MinIO artifact 다운로드
→ Kaniko가 Harbor에 predictive-model:v1.0.4 push
→ onExit에서 GitLab ECR sync pipeline trigger
→ GitLab이 Harbor image를 ECR로 copy
→ Argo Image Updater가 ECR predictive-model:v1.0.4 감지
→ public/k8s/serving/predictive-model/kustomization.yaml 갱신
→ Argo CD가 pdm-serving rollout
```
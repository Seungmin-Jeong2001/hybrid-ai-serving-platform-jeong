# GPU Worker Resources

이 디렉터리는 GPU worker의 Kubernetes 리소스 기준을 관리합니다.

## 담당 범위

- GPU RuntimeClass 기준
- NVIDIA device plugin 연동 기준
- GPU validation job 기준
- GPU node label/taint 계획

## 목표 역할

```text
GPU worker VM
  -> CUDA/NVIDIA runtime
  -> GitLab SSH runner execution target
  -> optional Kubernetes GPU node
```

# Terraform이 helm_release로 EKS 클러스터 안에 Argo CD를 설치하는 구조

resource "kubernetes_namespace" "argocd" {
  metadata {
    name = "argocd"
  }

  depends_on = [aws_eks_node_group.workloads]
}

resource "helm_release" "argocd" {
  name             = "argocd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  version          = var.argocd_chart_version
  namespace        = kubernetes_namespace.argocd.metadata[0].name
  create_namespace = false
  wait             = true
  timeout          = 900

  values = [
    yamlencode({
      global = {
        nodeSelector = {
          workload = "system"
        }
      }
      controller = {
        nodeSelector = {
          workload = "system"
        }
      }
      dex = {
        nodeSelector = {
          workload = "system"
        }
      }
      redis = {
        nodeSelector = {
          workload = "system"
        }
      }
      repoServer = {
        nodeSelector = {
          workload = "system"
        }
      }
      server = {
        nodeSelector = {
          workload = "system"
        }
      }
      applicationSet = {
        nodeSelector = {
          workload = "system"
        }
      }
      notifications = {
        nodeSelector = {
          workload = "system"
        }
      }
    })
  ]

  depends_on = [kubernetes_namespace.argocd]
}

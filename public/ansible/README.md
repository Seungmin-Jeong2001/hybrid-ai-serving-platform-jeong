# Ansible deployment

This directory contains the Ansible entrypoint for platform services deployed to EKS.

## Structure

- `site.yml`: top-level playbook entrypoint
- `requirements.yml`: required Ansible collections
- `roles/monitoring`: Grafana and Prometheus deployment role

## Prerequisites

- `aws` CLI installed and authenticated
- `kubectl` installed
- `helm` installed
- `ansible` installed
- access to the target EKS cluster

## Required variables

Create a variable file in your secure environment and provide at least:

- `grafana_admin_password`

Example file in this repository:

- `public/ansible/examples/monitoring.vars.yml.example`

You can copy the example from:

- `public/ansible/examples/monitoring.vars.yml.example`

## Install Ansible collections

```powershell
ansible-galaxy collection install -r public/ansible/requirements.yml
```

## Connect to EKS

```powershell
aws eks update-kubeconfig --region ap-northeast-2 --name sgs-hasp-eks
kubectl config current-context
kubectl get nodes
```

## Deploy monitoring stack

```powershell
ansible-playbook public/ansible/site.yml -e @monitoring.yml
```

## Verify deployment

```powershell
kubectl get ns monitoring
kubectl get pods -n monitoring
kubectl get svc -n monitoring
helm list -n monitoring
```

## Notes

- The monitoring role deploys the `kube-prometheus-stack` chart.
- Grafana and Prometheus pod settings are controlled through `roles/monitoring/templates/values.yaml.j2`.
- Do not commit real passwords to this repository.

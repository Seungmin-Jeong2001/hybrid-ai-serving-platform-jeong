# Example backend config for the GitLab OIDC / ECR promotion IAM module.
# Keep this module in remote state before using it from GitHub Actions.
bucket       = "sgs-hasp-tfstate"
key          = "private/aws-oidc/terraform.tfstate"
region       = "ap-northeast-2"
use_lockfile = true
encrypt      = true

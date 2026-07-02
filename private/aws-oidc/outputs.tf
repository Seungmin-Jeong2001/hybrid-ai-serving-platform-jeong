output "gitlab_oidc_provider_arn" {
  description = "ARN of the AWS IAM OIDC provider for GitLab."
  value       = aws_iam_openid_connect_provider.gitlab.arn
}

output "gitlab_ecr_promotion_role_arn" {
  description = "ARN of the IAM role assumed by GitLab CI for ECR promotion."
  value       = aws_iam_role.gitlab_ecr_promotion.arn
}

output "aws_role_arn_gitlab_variable" {
  description = "Convenience string for the GitLab CI/CD variable value."
  value       = aws_iam_role.gitlab_ecr_promotion.arn
}

# DynamoDB 테이블 - 고객사 대시보드용 추론 결과 저장
resource "aws_dynamodb_table" "inference_results" {
  name         = "${var.project_name}-inference-results"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "request_id"

  attribute {
    name = "request_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-inference-results"
  })
}

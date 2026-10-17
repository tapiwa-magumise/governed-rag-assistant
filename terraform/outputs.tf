output "app_role_arn" {
  value = aws_iam_role.app.arn
}

output "profiles" {
  value = { for k, p in aws_bedrock_inference_profile.this : k => p.arn }
}

output "guardrails" {
  value = {
    ingest = { id = aws_bedrock_guardrail.ingest.guardrail_id, version = aws_bedrock_guardrail_version.ingest.version }
    answer = { id = aws_bedrock_guardrail.answer.guardrail_id, version = aws_bedrock_guardrail_version.answer.version }
  }
}

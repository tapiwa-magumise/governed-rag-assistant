# The app runs as this role, never as the person running it. It may call the three inference profiles and
# the two guardrails, in London, and nothing else (N2).
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_role" "app" {
  name                 = "${var.name}-app"
  max_session_duration = 3600
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Whoever applied this Terraform can assume the role to run the app locally.
      {
        Effect    = "Allow"
        Principal = { AWS = data.aws_caller_identity.current.arn }
        Action    = "sts:AssumeRole"
      },
      # N9: the evaluation workflow signs in through GitHub's OIDC provider, with no stored keys.
      {
        Effect    = "Allow"
        Principal = { Federated = data.aws_iam_openid_connect_provider.github.arn }
        Action    = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" }
          StringLike   = { "token.actions.githubusercontent.com:sub" = "${var.github_oidc_subject}:*" }
        }
      },
    ]
  })
}

resource "aws_iam_role_policy" "app" {
  name = "bedrock"
  role = aws_iam_role.app.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "InvokeThroughTheProjectProfiles"
        Effect = "Allow"
        Action = ["bedrock:InvokeModel"]
        Resource = concat(
          [for p in aws_bedrock_inference_profile.this : p.arn],
          [for m in values(local.models) : "arn:aws:bedrock:${var.region}::foundation-model/${m}"],
        )
      },
      {
        Sid      = "ApplyTheProjectGuardrails"
        Effect   = "Allow"
        Action   = ["bedrock:ApplyGuardrail"]
        Resource = [aws_bedrock_guardrail.ingest.guardrail_arn, aws_bedrock_guardrail.answer.guardrail_arn]
      },
      {
        # Belt and braces for N2: refuse any Bedrock call outside London, whatever else is granted later.
        Sid       = "LondonOnly"
        Effect    = "Deny"
        Action    = ["bedrock:*"]
        Resource  = "*"
        Condition = { StringNotEquals = { "aws:RequestedRegion" = var.region } }
      },
    ]
  })
}

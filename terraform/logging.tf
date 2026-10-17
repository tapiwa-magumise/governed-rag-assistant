# Bedrock's own record of every model call, kept apart from the app's audit log, so the two can be compared.
# Prompts reaching the model are already masked, so these logs hold no personal data either (N1, N7).
resource "aws_cloudwatch_log_group" "invocations" {
  name              = "/${var.name}/bedrock-invocations"
  retention_in_days = 30
}

resource "aws_iam_role" "invocation_logging" {
  name = "${var.name}-invocation-logging"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "bedrock.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = { "aws:SourceAccount" = local.account_id }
        ArnLike      = { "aws:SourceArn" = "arn:aws:bedrock:${var.region}:${local.account_id}:*" }
      }
    }]
  })
}

resource "aws_iam_role_policy" "invocation_logging" {
  name = "write-logs"
  role = aws_iam_role.invocation_logging.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "${aws_cloudwatch_log_group.invocations.arn}:*"
    }]
  })
}

# Account-wide setting for the region. Embeddings aren't logged: the vectors add volume and no insight.
resource "aws_bedrock_model_invocation_logging_configuration" "this" {
  logging_config {
    text_data_delivery_enabled      = true
    embedding_data_delivery_enabled = false
    image_data_delivery_enabled     = false
    video_data_delivery_enabled     = false
    cloudwatch_config {
      log_group_name = aws_cloudwatch_log_group.invocations.name
      role_arn       = aws_iam_role.invocation_logging.arn
    }
  }
  depends_on = [aws_iam_role_policy.invocation_logging]
}

# N10: the build must cost under $10. Bedrock is used by nothing else in this account, so the budget
# watches the service as a whole; model calls through the tagged profiles are also visible by tag.
resource "aws_budgets_budget" "build" {
  count        = var.alert_email == "" ? 0 : 1
  name         = "${var.name}-build"
  budget_type  = "COST"
  limit_amount = tostring(var.budget_limit_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  cost_filter {
    name   = "Service"
    values = ["Amazon Bedrock"]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 50
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}

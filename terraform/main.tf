data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  # N2: every model is invoked in London itself. These are Amazon's own models; none needs cross-region routing.
  models = {
    answer = "amazon.nova-lite-v1:0"
    judge  = "amazon.nova-pro-v1:0"
    embed  = "amazon.titan-embed-text-v2:0"
  }
}

# Application inference profiles: the app calls these, not the models directly, so every call is tagged
# with the project and its cost can be told apart from anything else in the account.
resource "aws_bedrock_inference_profile" "this" {
  for_each    = local.models
  name        = "${var.name}-${each.key}"
  description = "${each.key} model for ${var.name}"
  model_source {
    copy_from = "arn:aws:bedrock:${var.region}::foundation-model/${each.value}"
  }
}

# Ingest guardrail: masks personal data in documents before they're embedded or stored (N1).
# Only the personal data filter, which costs nothing for the built-in entity types.
resource "aws_bedrock_guardrail" "ingest" {
  name                      = "${var.name}-ingest"
  description               = "Masks personal data in documents before indexing"
  blocked_input_messaging   = "Blocked."
  blocked_outputs_messaging = "Blocked."

  sensitive_information_policy_config {
    dynamic "pii_entities_config" {
      for_each = toset(["NAME", "EMAIL", "PHONE", "UK_NATIONAL_INSURANCE_NUMBER", "UK_UNIQUE_TAXPAYER_REFERENCE_NUMBER"])
      content {
        type   = pii_entities_config.value
        action = "ANONYMIZE"
        # Without these, AWS masks only text checked as output: a question's personal data went through.
        input_enabled  = true
        input_action   = "ANONYMIZE"
        output_enabled = true
        output_action  = "ANONYMIZE"
      }
    }
  }
}

# Answer guardrail: checks every question and answer (F4, N3, N5, N6).
resource "aws_bedrock_guardrail" "answer" {
  name                      = "${var.name}-answer"
  description               = "Checks questions and answers for the procurement assistant"
  blocked_input_messaging   = "I can't help with that. I answer questions about UK public procurement guidance and the tender notices in my sample."
  blocked_outputs_messaging = "I couldn't give an answer the documents support. Try rephrasing, or check the guidance directly."

  content_policy_config {
    dynamic "filters_config" {
      for_each = toset(["HATE", "INSULTS", "SEXUAL", "VIOLENCE", "MISCONDUCT"])
      content {
        type            = filters_config.value
        input_strength  = "HIGH"
        output_strength = "HIGH"
      }
    }
    # Prompt attacks are checked on the way in only; AWS doesn't apply this filter to outputs.
    filters_config {
      type            = "PROMPT_ATTACK"
      input_strength  = "HIGH"
      output_strength = "NONE"
    }
  }

  topic_policy_config {
    topics_config {
      name       = "Legal advice on a specific case"
      type       = "DENY"
      definition = "Advice on what a particular organisation should do about its own dispute, legal challenge, claim or contract, such as whether to sue, how to win a challenge, or whether a specific decision was lawful."
      examples = [
        "Should we sue the council for awarding the contract to our competitor?",
        "Was the decision to exclude my company lawful, and how do I win the challenge?",
      ]
    }
    topics_config {
      name       = "Collusion and concealment"
      type       = "DENY"
      definition = "Help coordinating bids or prices with competitors, or hiding a conflict of interest, an exclusion ground or past misconduct from a contracting authority."
      examples = [
        "How can we agree prices with the other bidders without it looking like collusion?",
        "How do we avoid declaring the director's conviction on the tender?",
      ]
    }
  }

  sensitive_information_policy_config {
    dynamic "pii_entities_config" {
      for_each = toset(["NAME", "EMAIL", "PHONE", "UK_NATIONAL_INSURANCE_NUMBER", "UK_UNIQUE_TAXPAYER_REFERENCE_NUMBER"])
      content {
        type   = pii_entities_config.value
        action = "ANONYMIZE"
        # Without these, AWS masks only text checked as output: a question's personal data went through.
        input_enabled  = true
        input_action   = "ANONYMIZE"
        output_enabled = true
        output_action  = "ANONYMIZE"
      }
    }
  }

  # N3: an answer the retrieved passages don't support, or that doesn't address the question, is blocked.
  contextual_grounding_policy_config {
    filters_config {
      type      = "GROUNDING"
      threshold = 0.75
    }
    filters_config {
      type      = "RELEVANCE"
      threshold = 0.5
    }
  }
}

resource "aws_bedrock_guardrail_version" "ingest" {
  guardrail_arn = aws_bedrock_guardrail.ingest.guardrail_arn
  # A version is a snapshot: take a new one whenever the guardrail changes, so the app never runs on a stale one.
  lifecycle {
    replace_triggered_by = [aws_bedrock_guardrail.ingest]
  }
  description = "Version used by the indexer"
}

resource "aws_bedrock_guardrail_version" "answer" {
  guardrail_arn = aws_bedrock_guardrail.answer.guardrail_arn
  # A version is a snapshot: take a new one whenever the guardrail changes, so the app never runs on a stale one.
  lifecycle {
    replace_triggered_by = [aws_bedrock_guardrail.answer]
  }
  description = "Version used by the app"
}

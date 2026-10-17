terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
  # Local state: everything here is deleted when the build is finished (N10), so nothing needs shared state.
}

locals {
  tags = { Project = "governed-rag", ManagedBy = "terraform" }
}

provider "aws" {
  region = var.region
  default_tags { tags = local.tags }
}

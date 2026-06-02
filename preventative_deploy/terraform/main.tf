terraform {
  required_version = ">= 1.3"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configured so `terraform plan` runs fully offline (no AWS calls, no cost):
# dummy creds + skip_* flags + the demo always plans with -refresh=false.
provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true

  default_tags {
    tags = var.tags
  }
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_security_group" "web" {
  name   = "${var.name}-web"
  vpc_id = aws_vpc.main.id

  ingress {
    description = "https"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.ingress_cidr]
  }
}

resource "aws_s3_bucket" "data" {
  bucket = var.bucket_name
}

# Toggled off in violation.tfvars to demonstrate the encryption policy firing.
resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  count  = var.enable_encryption ? 1 : 0
  bucket = var.bucket_name

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Toggled off in violation.tfvars to demonstrate the public-access policy firing.
resource "aws_s3_bucket_public_access_block" "data" {
  count                   = var.enable_public_access_block ? 1 : 0
  bucket                  = var.bucket_name
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

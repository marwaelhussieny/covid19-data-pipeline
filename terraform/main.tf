# Optional: provision a free-tier RDS Postgres instance instead of running
# Postgres locally via docker-compose. Not required to run the project —
# docker-compose is the default path — but shows the pipeline can target
# real cloud infra with one `terraform apply`.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "aws_region" {
  default = "us-east-1"
}

variable "db_password" {
  description = "Password for the covid_admin RDS user"
  type        = string
  sensitive   = true
}

provider "aws" {
  region = var.aws_region
}

resource "aws_db_instance" "covid_pipeline" {
  identifier              = "covid-pipeline-db"
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = "db.t3.micro" # AWS free-tier eligible
  allocated_storage       = 20            # free-tier eligible (up to 20GB)
  db_name                 = "covid"
  username                = "covid_admin"
  password                = var.db_password
  publicly_accessible     = true
  skip_final_snapshot     = true
  backup_retention_period = 1

  tags = {
    Project = "covid19-data-pipeline"
  }
}

output "rds_endpoint" {
  value = aws_db_instance.covid_pipeline.endpoint
}

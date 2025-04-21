terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  # Need to create S3 before hand
  backend "s3" {
    bucket         = "terraform-quantum-microservice-state-bucket"
    key            = "eks/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    # dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = "us-east-1"
}

# Don't forget to tag the subnets kubernetes.io/role/elb = "1"
# For each public subnet
# aws ec2 create-tags --resources subnet-xxxxxxxx --tags Key=kubernetes.io/role/elb,Value=1
# Kubernetes services of type LoadBalancer to automatically discover 
# these subnets, you often also need to tag the subnets with 
# kubernetes.io/cluster/eks1 = shared
module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  cluster_name    = "eks1"
  cluster_version = "1.28"
  subnet_ids      = ["subnet-0536a460c909e7014", "subnet-0b4c5332592f763c0"]  # Use your public subnet IDs
  vpc_id          = "vpc-0b43409b967dc118f"                        # Your VPC ID

  # Add this block
  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  enable_cluster_creator_admin_permissions = true
  
  eks_managed_node_groups = {
    default = {
      desired_capacity = 1
      max_capacity     = 2
      min_capacity     = 1

      instance_types = ["t3.medium"]
    }
  }
}

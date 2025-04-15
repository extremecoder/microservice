provider "aws" {
  region = "us-east-1"
}

module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  cluster_name    = "eks1"
  cluster_version = "1.28"
  subnets         = ["subnet-0536a460c909e7014", "subnet-0b4c5332592f763c0"]  # Use your subnet IDs
  vpc_id          = "vpc-0b43409b967dc118f"                        # Your VPC ID

  eks_managed_node_groups = {
    default = {
      desired_capacity = 1
      max_capacity     = 2
      min_capacity     = 1

      instance_types = ["t3.medium"]
    }
  }
}

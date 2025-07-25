=========================================
LearnTrac Infrastructure Testing
=========================================

ℹ️  Gathering infrastructure information...
ℹ️  Testing ALB connectivity...
✅ ALB is responding (HTTP 200)
   URL: http://hutch-learntrac-dev-alb-1826735098.us-east-2.elb.amazonaws.com/
ℹ️  Checking ECR repositories...
✅ Trac ECR repository exists
   URL: 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-trac
✅ LearnTrac ECR repository exists
   URL: 971422717446.dkr.ecr.us-east-2.amazonaws.com/hutch-learntrac-dev-learntrac
ℹ️  Checking ECS cluster and services...
✅ ECS cluster exists: hutch-learntrac-dev-cluster
✅ ECS services found
--------------------------------------------------
|                DescribeServices                |
+--------------------------------+----+----+-----+
|  hutch-learntrac-dev-trac      |  1 |  0 |  0  |
|  hutch-learntrac-dev-learntrac |  1 |  0 |  0  |
+--------------------------------+----+----+-----+
ℹ️  Checking Redis endpoint...
✅ Redis endpoint configured: hutch-learntrac-dev-redis.wda3jc.0001.use2.cache.amazonaws.com
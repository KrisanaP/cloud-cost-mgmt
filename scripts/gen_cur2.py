"""
Synthetic AWS CUR 2.0 generator — enterprise-style workload for practising FinOps / building a
Datadog-like Cloud Cost Management tool.

Column names follow the CUR 2.0 table dictionary:
https://docs.aws.amazon.com/cur/latest/userguide/table-dictionary-cur2.html

Prices are approximate (roughly ap-southeast-1 public on-demand) and only meant to look plausible.
Simplifications vs. real CUR 2.0:
  * daily granularity (real exports can be hourly)
  * a subset of columns (~60 of ~125); nested columns (product, resource_tags, cost_category,
    discount) are JSON strings here, map<string,string> in real Parquet exports
  * EKS split cost allocation columns (split_line_item_*) are not simulated

Usage:  python3 scripts/gen_cur2.py [--start 2026-07-01] [--days 92] [--seed 42] [--out data/cur2_sample]
"""
import argparse, hashlib, json, random
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--start", default="2026-07-01")
ap.add_argument("--days", type=int, default=92)
ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--out", default="data/cur2_sample")
args = ap.parse_args()
random.seed(args.seed); np.random.seed(args.seed)

START = datetime.fromisoformat(args.start)
DAYS = args.days

# --------------------------------------------------------------------------- organisation
PAYER_ID, PAYER_NAME = "111111111111", "acme-payer"
ACCOUNTS = {  # name: (id, environment, business_unit, team pool)
    "acme-payer":    ("111111111111", "shared",  "corporate",   ["platform"]),
    "acme-prod":     ("222222222222", "prod",    "engineering", ["payments", "search", "web", "mobile", "platform"]),
    "acme-staging":  ("333333333333", "staging", "engineering", ["payments", "search", "web", "mobile", "platform"]),
    "acme-dev":      ("444444444444", "dev",     "engineering", ["payments", "search", "web", "mobile", "platform"]),
    "acme-data":     ("555555555555", "prod",    "analytics",   ["data"]),
    "acme-network":  ("666666666666", "shared",  "engineering", ["platform"]),
    "acme-security": ("777777777777", "shared",  "security",    ["security"]),
}
APP = ["acme-prod", "acme-staging", "acme-dev"]
REGION_CODE = {"ap-southeast-1": "APS1", "us-east-1": "USE1", "global": "GLOBAL"}
REGION_NAME = {"ap-southeast-1": "Asia Pacific (Singapore)", "us-east-1": "US East (N. Virginia)", "global": "Global"}
# messy tag values on purpose → exercise for a tag pipeline
TEAM_SPELLINGS = {"payments": ["payments", "payments", "Payments", "payment"], "search": ["search", "search", "Search"]}
SERVICES = {"payments": ["payment-api", "ledger"], "search": ["search-api", "indexer"], "web": ["storefront"],
            "mobile": ["mobile-bff"], "platform": ["shared-infra", "eks-platform"], "data": ["etl", "analytics", "ml"],
            "security": ["sec-tooling"]}

# --------------------------------------------------------------------------- catalog
def I(key, code, name, ut, op, unit, rate, fam, qty, accts, n=1, rid=None, region="ap-southeast-1",
      az=False, itype=None, prod=None, team=None, daily_fixed=False):
    return dict(key=key, code=code, name=name, ut=ut, op=op, unit=unit, rate=rate, fam=fam, qty=qty, accts=accts,
                n=n, rid=rid, region=region, az=az, itype=itype, prod=prod or {}, team=team, daily_fixed=daily_fixed)

M = 1 / 30.4  # monthly price → per-day for GB-Mo style units (qty is GB held that day)
EC2, RDS, S3 = "Amazon Elastic Compute Cloud", "Amazon Relational Database Service", "Amazon Simple Storage Service"

CATALOG = [
    # ---- compute ---------------------------------------------------------------------------
    I("ec2_app", "AmazonEC2", EC2, "BoxUsage:m6i.large", "RunInstances", "Hrs", 0.12, "Compute Instance", (24, 24),
      APP, n={"acme-prod": 4, "acme-staging": 2, "acme-dev": 2}, rid="i", az=True, itype="m6i.large",
      prod={"operating_system": "Linux", "tenancy": "Shared"}),
    I("eks_node", "AmazonEC2", EC2, "BoxUsage:m6i.xlarge", "RunInstances", "Hrs", 0.24, "Compute Instance", (24, 24),
      ["acme-prod", "acme-staging"], n={"acme-prod": 6, "acme-staging": 2}, rid="i", az=True, itype="m6i.xlarge",
      prod={"operating_system": "Linux"}, team="platform"),
    I("ec2_batch_spot", "AmazonEC2", EC2, "SpotUsage:c6i.2xlarge", "RunInstances:SV001", "Hrs", 0.13, "Compute Instance",
      (4, 20), ["acme-data"], n=4, rid="i", az=True, itype="c6i.2xlarge", prod={"operating_system": "Linux"}),
    I("ec2_gpu", "AmazonEC2", EC2, "BoxUsage:g5.xlarge", "RunInstances", "Hrs", 1.29, "Compute Instance", (24, 24),
      ["acme-dev"], rid="i", az=True, itype="g5.xlarge", prod={"operating_system": "Linux"}),
    I("eks_cluster", "AmazonEKS", "Amazon Elastic Container Service for Kubernetes", "AmazonEKS-Hours:perCluster",
      "CreateOperation", "Hrs", 0.10, "Compute", (24, 24), ["acme-prod", "acme-staging"], rid="eks", team="platform"),
    I("fargate_cpu", "AmazonECS", "Amazon Elastic Container Service", "Fargate-vCPU-Hours:perCPU", "FargateTask",
      "hours", 0.05056, "Compute", (24, 96), APP, n={"acme-prod": 4, "acme-staging": 2, "acme-dev": 2}, rid="ecs"),
    I("fargate_mem", "AmazonECS", "Amazon Elastic Container Service", "Fargate-GB-Hours", "FargateTask", "hours",
      0.00553, "Compute", (48, 192), APP, n={"acme-prod": 4, "acme-staging": 2, "acme-dev": 2}, rid="ecs"),
    I("lambda_gbs", "AWSLambda", "AWS Lambda", "Lambda-GB-Second", "Invoke", "Lambda-GB-Second", 0.0000166667,
      "Serverless", (50_000, 400_000), APP + ["acme-data"], n=3, rid="lambda"),
    I("lambda_req", "AWSLambda", "AWS Lambda", "Request", "Invoke", "Requests", 0.0000002, "Serverless",
      (200_000, 2_000_000), APP + ["acme-data"], n=3, rid="lambda"),
    I("ecr", "AmazonECR", "Amazon EC2 Container Registry (ECR)", "TimedStorage-ByteHrs", "", "GB-Mo", 0.10 * M,
      "EC2 Container Registry", (80, 300), ["acme-network"], rid="ecr", team="platform"),
    # ---- EC2-Other (EBS, snapshots, NAT, inter-AZ transfer) -----------------------------
    I("ebs_gp3", "AmazonEC2", EC2, "EBS:VolumeUsage.gp3", "CreateVolume-Gp3", "GB-Mo", 0.096 * M, "Storage",
      (100, 500), APP + ["acme-data"], n=4, rid="vol", az=True, prod={"volume_api_name": "gp3"}),
    I("ebs_gp2", "AmazonEC2", EC2, "EBS:VolumeUsage.gp2", "CreateVolume-Gp2", "GB-Mo", 0.12 * M, "Storage",
      (200, 800), ["acme-staging", "acme-dev"], n=3, rid="vol", az=True, prod={"volume_api_name": "gp2"}),
    I("ebs_snap", "AmazonEC2", EC2, "EBS:SnapshotUsage", "CreateSnapshot", "GB-Mo", 0.05 * M, "Storage Snapshot",
      (500, 3000), APP + ["acme-data"], n=2, rid="snap"),
    I("nat_hours", "AmazonEC2", EC2, "NatGateway-Hours", "NatGateway", "Hrs", 0.059, "NAT Gateway", (24, 24),
      ["acme-network", "acme-prod", "acme-data"], n={"acme-network": 3, "acme-prod": 3, "acme-data": 1}, rid="nat", team="platform"),
    I("nat_bytes", "AmazonEC2", EC2, "NatGateway-Bytes", "NatGateway", "GB", 0.059, "NAT Gateway", (40, 160),
      ["acme-network", "acme-prod", "acme-data"], n={"acme-network": 3, "acme-prod": 3, "acme-data": 1}, rid="nat", team="platform"),
    I("dt_regional", "AmazonEC2", EC2, "DataTransfer-Regional-Bytes", "InterZone-In", "GB", 0.01, "Data Transfer",
      (100, 900), ["acme-prod", "acme-data"], prod={"transfer_type": "IntraRegion"}),
    # ---- networking ------------------------------------------------------------------------
    I("alb_hours", "AWSELB", "Elastic Load Balancing", "LoadBalancerUsage", "LoadBalancing:Application", "Hrs", 0.0252,
      "Load Balancer-Application", (24, 24), APP, n={"acme-prod": 3, "acme-staging": 2, "acme-dev": 2}, rid="alb"),
    I("alb_lcu", "AWSELB", "Elastic Load Balancing", "LCUUsage", "LoadBalancing:Application", "LCU-Hrs", 0.008,
      "Load Balancer-Application", (30, 400), APP, n={"acme-prod": 3, "acme-staging": 2, "acme-dev": 2}, rid="alb"),
    I("ipv4_inuse", "AmazonVPC", "Amazon Virtual Private Cloud", "PublicIPv4:InUseAddress", "AssociateAddressVPC",
      "Hrs", 0.005, "IP Address", (24, 24), ["acme-prod", "acme-network"], n=6, rid="eip"),
    I("ipv4_idle", "AmazonVPC", "Amazon Virtual Private Cloud", "PublicIPv4:IdleAddress", "AllocateAddressVPC",
      "Hrs", 0.005, "IP Address", (24, 24), ["acme-dev", "acme-staging"], n=3, rid="eip"),
    I("tgw_hours", "AmazonVPC", "Amazon Virtual Private Cloud", "TransitGateway-Hours", "TransitGatewayVPC", "Hrs",
      0.07, "Transit Gateway", (24, 24), ["acme-network"], n=5, rid="tgw", team="platform"),
    I("tgw_bytes", "AmazonVPC", "Amazon Virtual Private Cloud", "TransitGateway-Bytes", "TransitGatewayVPC", "GB",
      0.02, "Transit Gateway", (50, 400), ["acme-network"], rid="tgw", team="platform"),
    I("vpce", "AmazonVPC", "Amazon Virtual Private Cloud", "VpcEndpoint-Hours", "VpcEndpoint", "Hrs", 0.013,
      "VpcEndpoint", (24, 24), ["acme-network"], n=8, rid="vpce", team="platform"),
    I("dt_out", "AWSDataTransfer", "AWS Data Transfer", "DataTransfer-Out-Bytes", "", "GB", 0.12, "Data Transfer",
      (20, 120), ["acme-prod", "acme-data"], prod={"transfer_type": "AWS Outbound"}),
    I("cf_out", "AmazonCloudFront", "Amazon CloudFront", "AP-DataTransfer-Out-Bytes", "GET", "GB", 0.12,
      "Data Transfer", (300, 1200), ["acme-prod"], rid="cf", region="global", team="web"),
    I("cf_req", "AmazonCloudFront", "Amazon CloudFront", "AP-Requests-Tier2-HTTPS", "GET", "Requests", 0.0000012,
      "Request", (3_000_000, 12_000_000), ["acme-prod"], rid="cf", region="global", team="web"),
    I("r53_zone", "AmazonRoute53", "Amazon Route 53", "HostedZone", "", "HostedZone", 0.5 * M, "DNS Zone", (1, 1),
      ["acme-network"], n=6, rid="r53", region="global", team="platform", daily_fixed=True),
    I("r53_query", "AmazonRoute53", "Amazon Route 53", "DNS-Queries", "", "Queries", 0.0000004, "DNS Query",
      (5_000_000, 20_000_000), ["acme-network"], rid="r53", region="global", team="platform"),
    # ---- storage ---------------------------------------------------------------------------
    I("s3_std", "AmazonS3", S3, "TimedStorage-ByteHrs", "StandardStorage", "GB-Mo", 0.025 * M, "Storage",
      (500, 4000), APP + ["acme-data"], n=3, rid="s3", prod={"storage_class": "General Purpose"}),
    I("s3_ia", "AmazonS3", S3, "TimedStorage-SIA-ByteHrs", "StandardIAStorage", "GB-Mo", 0.0138 * M, "Storage",
      (2000, 9000), ["acme-prod", "acme-data"], rid="s3", prod={"storage_class": "Infrequent Access"}),
    I("s3_gir", "AmazonS3", S3, "TimedStorage-GIR-ByteHrs", "GlacierInstantRetrievalStorage", "GB-Mo", 0.005 * M,
      "Storage", (10_000, 40_000), ["acme-data"], rid="s3", prod={"storage_class": "Archive Instant Retrieval"}),
    I("s3_dr", "AmazonS3", S3, "TimedStorage-ByteHrs", "StandardStorage", "GB-Mo", 0.023 * M, "Storage",
      (3000, 6000), ["acme-data"], rid="s3", region="us-east-1", prod={"storage_class": "General Purpose"}),
    I("s3_put", "AmazonS3", S3, "Requests-Tier1", "PutObject", "Requests", 0.000005, "API Request",
      (50_000, 600_000), APP + ["acme-data"], n=3, rid="s3"),
    I("s3_get", "AmazonS3", S3, "Requests-Tier2", "GetObject", "Requests", 0.0000004, "API Request",
      (500_000, 6_000_000), APP + ["acme-data"], n=3, rid="s3"),
    I("efs", "AmazonEFS", "Amazon Elastic File System", "TimedStorage-ByteHrs", "", "GB-Mo", 0.36 * M, "Storage",
      (50, 400), ["acme-prod", "acme-data"], rid="efs"),
    I("backup_ebs", "AWSBackup", "AWS Backup", "WarmStorage-ByteHrs-EBS", "Storage", "GB-Mo", 0.05 * M,
      "Storage", (2000, 6000), ["acme-prod", "acme-data"], rid="backup", team="platform"),
    I("backup_rds", "AWSBackup", "AWS Backup", "WarmStorage-ByteHrs-RDS", "Storage", "GB-Mo", 0.095 * M,
      "Storage", (800, 2500), ["acme-prod"], rid="backup", team="platform"),
    I("backup_cold", "AWSBackup", "AWS Backup", "ColdStorage-ByteHrs-EFS", "Storage", "GB-Mo", 0.01 * M,
      "Storage", (5000, 15000), ["acme-security"], rid="backup", team="security"),
    # ---- databases -------------------------------------------------------------------------
    I("rds_multiaz", "AmazonRDS", RDS, "Multi-AZUsage:db.r6g.xl", "CreateDBInstance:0014", "Hrs", 1.06,
      "Database Instance", (24, 24), ["acme-prod"], n=2, rid="rds", az=True, itype="db.r6g.xlarge",
      prod={"database_engine": "PostgreSQL", "deployment_option": "Multi-AZ"}),
    I("rds_single", "AmazonRDS", RDS, "InstanceUsage:db.t4g.large", "CreateDBInstance:0014", "Hrs", 0.17,
      "Database Instance", (24, 24), ["acme-staging", "acme-dev"], n=2, rid="rds", az=True, itype="db.t4g.large",
      prod={"database_engine": "PostgreSQL", "deployment_option": "Single-AZ"}),
    I("rds_storage", "AmazonRDS", RDS, "RDS:Multi-AZ-GP3-Storage", "CreateDBInstance:0014", "GB-Mo", 0.276 * M,
      "Database Storage", (500, 2000), ["acme-prod"], n=2, rid="rds"),
    I("rds_backup", "AmazonRDS", RDS, "RDS:ChargedBackupUsage", "", "GB-Mo", 0.095 * M, "Storage Snapshot",
      (300, 1500), ["acme-prod", "acme-staging"], rid="rds"),
    I("aurora", "AmazonRDS", RDS, "InstanceUsage:db.r6g.large", "CreateDBInstance:0021", "Hrs", 0.32,
      "Database Instance", (24, 24), ["acme-data"], n=2, rid="rds", az=True, itype="db.r6g.large",
      prod={"database_engine": "Aurora PostgreSQL"}),
    I("aurora_io", "AmazonRDS", RDS, "Aurora:StorageIOUsage", "", "IOs", 0.00000022, "System Operation",
      (20_000_000, 90_000_000), ["acme-data"], rid="rds"),
    I("ddb_wru", "AmazonDynamoDB", "Amazon DynamoDB", "WriteRequestUnits", "PayPerRequestThroughput", "WriteRequestUnits",
      0.0000014325, "Amazon DynamoDB PayPerRequest Throughput", (2_000_000, 15_000_000), APP, n=2, rid="ddb"),
    I("ddb_rru", "AmazonDynamoDB", "Amazon DynamoDB", "ReadRequestUnits", "PayPerRequestThroughput", "ReadRequestUnits",
      0.000000285, "Amazon DynamoDB PayPerRequest Throughput", (10_000_000, 60_000_000), APP, n=2, rid="ddb"),
    I("ddb_storage", "AmazonDynamoDB", "Amazon DynamoDB", "TimedStorage-ByteHrs", "", "GB-Mo", 0.285 * M,
      "Database Storage", (50, 600), APP, n=2, rid="ddb"),
    I("elasticache", "AmazonElastiCache", "Amazon ElastiCache", "NodeUsage:cache.r6g.large", "CreateCacheCluster:0002",
      "Hrs", 0.247, "Cache Instance", (24, 24), ["acme-prod", "acme-staging"], n={"acme-prod": 3, "acme-staging": 1},
      rid="cache", itype="cache.r6g.large"),
    I("opensearch", "AmazonES", "Amazon OpenSearch Service", "ESInstance:r6g.large", "ESDomain", "Hrs", 0.193,
      "Amazon OpenSearch Service Instance", (24, 24), ["acme-prod"], n=3, rid="es", team="search", itype="r6g.large.search"),
    I("redshift", "AmazonRedshift", "Amazon Redshift", "Node:ra3.xlplus", "RunComputeNode:0001", "Hrs", 1.303,
      "Compute Instance", (24, 24), ["acme-data"], n=2, rid="redshift", itype="ra3.xlplus"),
    # ---- integration / messaging ---------------------------------------------------------
    I("sqs", "AWSQueueService", "Amazon Simple Queue Service", "Requests-RBP", "", "Requests", 0.0000004,
      "Message Queue", (5_000_000, 40_000_000), APP + ["acme-data"], n=2, rid="sqs"),
    I("sqs_fifo", "AWSQueueService", "Amazon Simple Queue Service", "Requests-FIFO-RBP", "", "Requests", 0.0000005,
      "Message Queue", (1_000_000, 6_000_000), ["acme-prod"], rid="sqs", team="payments"),
    I("sns", "AmazonSNS", "Amazon Simple Notification Service", "Requests-Tier1", "", "Requests", 0.0000005,
      "Message Delivery", (1_000_000, 8_000_000), APP, rid="sns"),
    I("sns_sms", "AmazonSNS", "Amazon Simple Notification Service", "DeliveryAttempts-SMS", "", "Notifications",
      0.0263, "Message Delivery", (200, 1500), ["acme-prod"], rid="sns", team="mobile"),
    I("eventbridge", "AWSEvents", "Amazon EventBridge", "Event-64K-Chunks", "PutEvents", "Events", 0.000001,
      "EventBridge", (2_000_000, 10_000_000), ["acme-prod", "acme-data"], rid="events"),
    I("sfn", "AWSStepFunctions", "AWS Step Functions", "StateTransition", "", "StateTransitions", 0.000025,
      "AWS Step Functions", (50_000, 400_000), ["acme-prod", "acme-data"], rid="sfn"),
    I("apigw", "AmazonApiGateway", "Amazon API Gateway", "ApiGatewayRequest", "ApiGatewayRequest", "Requests",
      0.0000035, "API Calls", (1_000_000, 8_000_000), ["acme-prod", "acme-staging"], rid="apigw"),
    I("kinesis", "AmazonKinesis", "Amazon Kinesis", "Storage-ShardHour", "", "ShardHour", 0.018, "Kinesis Streams",
      (96, 192), ["acme-data"], rid="kinesis"),
    I("msk", "AmazonMSK", "Amazon Managed Streaming for Apache Kafka", "Kafka.m5.large", "", "Hrs", 0.252,
      "Managed Streaming for Apache Kafka (MSK)", (24, 24), ["acme-data"], n=3, rid="msk", itype="kafka.m5.large"),
    # ---- analytics / AI ------------------------------------------------------------------
    I("athena", "AmazonAthena", "Amazon Athena", "DataScannedInTB", "RunQuery", "Terabytes", 5.0,
      "Data Scanned", (0.2, 2.5), ["acme-data"], rid="athena"),
    I("glue", "AWSGlue", "AWS Glue", "GlueETL-DPU-Hour", "GlueJob", "DPU-Hour", 0.44, "AWS Glue",
      (4, 30), ["acme-data"], n=3, rid="glue"),
    I("bedrock_in", "AmazonBedrock", "Amazon Bedrock", "Claude-InputTokenCount", "InvokeModel", "1K tokens", 0.003,
      "Amazon Bedrock", (6_000, 20_000), ["acme-prod"], rid="bedrock", team="search"),
    I("bedrock_out", "AmazonBedrock", "Amazon Bedrock", "Claude-OutputTokenCount", "InvokeModel", "1K tokens", 0.015,
      "Amazon Bedrock", (800, 3_000), ["acme-prod"], rid="bedrock", team="search"),
    # ---- management / security -----------------------------------------------------------
    I("cw_logs", "AmazonCloudWatch", "AmazonCloudWatch", "DataProcessing-Bytes", "PutLogEvents", "GB", 0.67,
      "Data Payload", (4, 15), APP + ["acme-data"], rid=None),
    I("cw_metrics", "AmazonCloudWatch", "AmazonCloudWatch", "CW:MetricMonitorUsage", "MetricStorage", "Metrics",
      0.30 * M, "Metric", (2000, 2000), APP + ["acme-data"], rid=None, daily_fixed=True),
    I("cloudtrail", "AWSCloudTrail", "AWS CloudTrail", "PaidEventsRecorded", "", "Events", 0.00002, "Management Tools",
      (200_000, 800_000), ["acme-security"], rid="trail", team="security"),
    I("config", "AWSConfig", "AWS Config", "ConfigurationItemRecorded", "", "ConfigurationItemRecorded", 0.003,
      "Management Tools - AWS Config", (300, 1500), list(ACCOUNTS), team="security"),
    I("guardduty", "AmazonGuardDuty", "Amazon GuardDuty", "PaidEventsAnalyzed", "", "Events", 0.0000046,
      "Security Services", (1_000_000, 4_000_000), ["acme-security"], team="security"),
    I("securityhub", "AWSSecurityHub", "AWS Security Hub", "PaidComplianceCheck", "", "Checks", 0.001,
      "Security Services", (4000, 9000), ["acme-security"], team="security"),
    I("kms_keys", "awskms", "AWS Key Management Service", "KMS-Keys", "CreateKey", "Keys", 1.0 * M, "Encryption Key",
      (40, 40), ["acme-security"], team="security", daily_fixed=True),
    I("kms_req", "awskms", "AWS Key Management Service", "KMS-Requests", "Decrypt", "Requests", 0.000003,
      "API Request", (2_000_000, 9_000_000), ["acme-security"], team="security"),
    I("secrets", "AWSSecretsManager", "AWS Secrets Manager", "AWSSecretsManager-Secrets", "", "Secrets", 0.40 * M,
      "Secret", (120, 120), ["acme-prod", "acme-staging"], team="platform", daily_fixed=True),
    I("waf_acl", "awswaf", "AWS WAF", "WebACL", "", "WebACL", 5.0 * M, "Web Application Firewall", (3, 3),
      ["acme-prod"], team="security", daily_fixed=True),
    I("waf_req", "awswaf", "AWS WAF", "Request", "", "Requests", 0.0000006, "Web Application Firewall",
      (5_000_000, 20_000_000), ["acme-prod"], team="security"),
]

# --------------------------------------------------------------------------- helpers
def h(*parts, n=17):
    return hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()[:n]

def resource_id(item, acct, k, region, team, svc):
    acct_id = ACCOUNTS[acct][0]
    p, s = item["rid"], h(item["key"], acct, k)
    if p is None:
        return ""
    reg = "ap-southeast-1" if region == "global" else region
    return {
        "i": f"i-{s}", "vol": f"vol-{s}", "snap": f"arn:aws:ec2:{reg}:{acct_id}:snapshot/snap-{s}",
        "nat": f"arn:aws:ec2:{reg}:{acct_id}:natgateway/nat-{s}", "eip": f"arn:aws:ec2:{reg}:{acct_id}:ipv4pool-ec2/eipalloc-{s}",
        "tgw": f"arn:aws:ec2:{reg}:{acct_id}:transit-gateway/tgw-{s}", "vpce": f"arn:aws:ec2:{reg}:{acct_id}:vpc-endpoint/vpce-{s}",
        "eks": f"arn:aws:eks:{reg}:{acct_id}:cluster/{ACCOUNTS[acct][1]}-main",
        "ecs": f"arn:aws:ecs:{reg}:{acct_id}:service/{ACCOUNTS[acct][1]}-cluster/{svc}",
        "lambda": f"arn:aws:lambda:{reg}:{acct_id}:function:{svc}-fn{k}",
        "ecr": f"arn:aws:ecr:{reg}:{acct_id}:repository/acme-images",
        "alb": f"arn:aws:elasticloadbalancing:{reg}:{acct_id}:loadbalancer/app/{svc}-alb/{h(acct, k, n=16)}",
        "cf": f"arn:aws:cloudfront::{acct_id}:distribution/E{h(acct, n=13).upper()}",
        "r53": f"arn:aws:route53:::hostedzone/Z{h(acct, k, n=12).upper()}",
        "s3": f"acme-{ACCOUNTS[acct][1]}-{svc}-{h(item['key'], acct, k, n=6)}",
        "efs": f"arn:aws:elasticfilesystem:{reg}:{acct_id}:file-system/fs-{s}",
        "backup": f"arn:aws:backup:{reg}:{acct_id}:backup-vault:{ACCOUNTS[acct][1]}-vault",
        "rds": f"arn:aws:rds:{reg}:{acct_id}:db:{svc}-db-{k}",
        "ddb": f"arn:aws:dynamodb:{reg}:{acct_id}:table/{svc}-table{k}",
        "cache": f"arn:aws:elasticache:{reg}:{acct_id}:cluster:{svc}-cache-{k}",
        "es": f"arn:aws:es:{reg}:{acct_id}:domain/search-{k}",
        "redshift": f"arn:aws:redshift:{reg}:{acct_id}:cluster:analytics-dw",
        "sqs": f"arn:aws:sqs:{reg}:{acct_id}:{svc}-queue{k}", "sns": f"arn:aws:sns:{reg}:{acct_id}:{svc}-topic",
        "events": f"arn:aws:events:{reg}:{acct_id}:event-bus/default",
        "sfn": f"arn:aws:states:{reg}:{acct_id}:stateMachine:{svc}-flow",
        "apigw": f"arn:aws:apigateway:{reg}::/restapis/{h(acct, n=10)}",
        "kinesis": f"arn:aws:kinesis:{reg}:{acct_id}:stream/clickstream", "msk": f"arn:aws:kafka:{reg}:{acct_id}:cluster/events/{s}",
        "athena": f"arn:aws:athena:{reg}:{acct_id}:workgroup/primary", "glue": f"arn:aws:glue:{reg}:{acct_id}:job/{svc}-job{k}",
        "bedrock": f"arn:aws:bedrock:{reg}::foundation-model/anthropic.claude",
        "trail": f"arn:aws:cloudtrail:{reg}:{acct_id}:trail/org-trail",
    }[p]

def n_of(item, acct):
    return item["n"][acct] if isinstance(item["n"], dict) else item["n"]

REQUEST_UNITS = {"Requests", "Lambda-GB-Second", "GB", "Events", "Queries", "WriteRequestUnits", "ReadRequestUnits",
                 "StateTransitions", "Notifications", "1K tokens", "LCU-Hrs", "hours"}

def quantity(item, acct, day, d, k):
    """Return usage for one resource-day, or None if the resource did not run. Story lines live here."""
    key = item["key"]
    lo, hi = item["qty"]
    q = float(np.random.uniform(lo, hi))
    env = ACCOUNTS[acct][1]
    if env == "staging" and item["unit"] not in ("Hrs", "HostedZone"):
        q *= 0.3
    if env == "dev" and item["unit"] not in ("Hrs", "HostedZone"):
        q *= 0.15
    if item["unit"] in REQUEST_UNITS:
        if day.weekday() >= 5:
            q *= 0.6
        q *= 1 + 0.003 * d                                          # steady business growth
    if item["unit"] == "GB-Mo" and not item["daily_fixed"]:
        q = (lo + hi) / 2 * (1 + 0.002 * d) * (1 + 0.1 * (k % 3))   # storage grows smoothly
        if env == "staging": q *= 0.3
        if env == "dev": q *= 0.15

    # --- story 1: EKS prod scaled from 6 → 4 nodes on 1 Sep (Savings Plan under-utilised)
    if key == "eks_node" and acct == "acme-prod" and k >= 4 and day >= datetime(2026, 9, 1):
        return None
    # --- story 2: NAT Gateway data processing spike in prod 12–16 Aug
    if key == "nat_bytes" and acct == "acme-prod" and datetime(2026, 8, 12) <= day <= datetime(2026, 8, 16):
        q *= 4.5
    # --- story 3: forgotten GPU instance in dev from 8 Sep, never stopped, untagged
    if key == "ec2_gpu" and day < datetime(2026, 9, 8):
        return None
    # --- story 4: data account S3 Standard jumps 3.5x from 19 Sep (raw dumps without lifecycle)
    if key == "s3_std" and acct == "acme-data" and day >= datetime(2026, 9, 19):
        q *= 3.5
    # --- story 5: CloudWatch Logs ingestion in prod keeps growing (debug logging left on)
    if key == "cw_logs" and acct == "acme-prod":
        q *= 1 + 0.015 * d
    # --- story 6: new AI spend — Bedrock starts 22 Sep
    if key.startswith("bedrock") and day < datetime(2026, 9, 22):
        return None
    # dev app instances stop on weekends? No — they run 24/7 (story 7: candidate for scheduling)
    return q

def tags_for(item, acct, k):
    """Deterministic tags per resource; ~15% untagged; some messy spellings."""
    rnd = random.Random(h(item["key"], acct, k))
    env = ACCOUNTS[acct][1]
    team = item["team"] or rnd.choice(ACCOUNTS[acct][3])
    svc = rnd.choice(SERVICES[team])
    if item["key"] == "ec2_gpu":                       # the forgotten instance: no tags at all
        return {}, team, svc
    if item["rid"] is None and item["key"].startswith("cw"):
        return {"user_env": env}, team, svc
    if rnd.random() < 0.15:                            # untagged resource
        return {"user_env": env} if rnd.random() < 0.5 else {}, team, svc
    shown = rnd.choice(TEAM_SPELLINGS.get(team, [team]))
    tags = {"user_team": shown, "user_env": env, "user_service": svc}
    if rnd.random() < 0.7:
        tags["user_cost_center"] = {"payments": "CC-1001", "search": "CC-1002", "web": "CC-1003", "mobile": "CC-1004",
                                    "platform": "CC-2001", "data": "CC-3001", "security": "CC-4001"}[team]
    if item["key"] == "eks_node":
        tags["aws_eks_cluster_name"] = f"{env}-main"
        tags["aws_autoscaling_group_name"] = f"eks-{env}-main-ng"
    return tags, team, svc

# --------------------------------------------------------------------------- generate
SP_ARN = "arn:aws:savingsplans::111111111111:savingsplan/sp-0compute1yr"
SP_DISCOUNT = 0.72                    # SP rate = 72% of on-demand
SP_COMMIT_HOURLY = 1.10               # $/hour commitment
RI_ARN = "arn:aws:rds:ap-southeast-1:222222222222:ri:payments-db-ri"
RI_EFFECTIVE_RATE = 0.69              # $/hr effective for db.r6g.xl Multi-AZ under a 1yr No Upfront RI

def period_bounds(day):
    s = day.replace(day=1)
    e = (s + timedelta(days=32)).replace(day=1)
    return s, e

def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

rows = []

def base_row(acct, day_start, day_end):
    ps, pe = period_bounds(day_start)
    acct_id, env, bu, _ = ACCOUNTS[acct]
    return {
        "bill_bill_type": "Anniversary", "bill_billing_entity": "AWS",
        "bill_billing_period_start_date": iso(ps), "bill_billing_period_end_date": iso(pe),
        "bill_invoice_id": "", "bill_invoicing_entity": "Amazon Web Services, Inc.",
        "bill_payer_account_id": PAYER_ID, "bill_payer_account_name": PAYER_NAME,
        "identity_line_item_id": "", "identity_time_interval": f"{iso(day_start)}/{iso(day_end)}",
        "line_item_usage_account_id": acct_id, "line_item_usage_account_name": acct,
        "line_item_line_item_type": "Usage",
        "line_item_usage_start_date": iso(day_start), "line_item_usage_end_date": iso(day_end),
        "line_item_product_code": "", "line_item_usage_type": "", "line_item_operation": "",
        "line_item_availability_zone": "", "line_item_resource_id": "",
        "line_item_usage_amount": 0.0, "line_item_normalization_factor": 0.0, "line_item_normalized_usage_amount": 0.0,
        "line_item_currency_code": "USD", "line_item_unblended_rate": 0.0, "line_item_unblended_cost": 0.0,
        "line_item_blended_rate": 0.0, "line_item_blended_cost": 0.0,
        "line_item_net_unblended_rate": 0.0, "line_item_net_unblended_cost": 0.0,
        "line_item_line_item_description": "", "line_item_legal_entity": "Amazon Web Services, Inc.",
        "line_item_tax_type": "",
        "pricing_public_on_demand_cost": 0.0, "pricing_public_on_demand_rate": 0.0,
        "pricing_term": "", "pricing_unit": "", "pricing_purchase_option": "",
        "product_product_family": "", "product_servicecode": "", "product_region_code": "", "product_location": "",
        "product_instance_type": "", "product_instance_family": "", "product_sku": "",
        "product_from_location": "", "product_to_location": "",
        "product": "{}", "resource_tags": "{}",
        "cost_category": json.dumps({"business_unit": bu, "environment": env}), "discount": "{}",
        "reservation_reservation_a_r_n": "", "reservation_effective_cost": 0.0,
        "reservation_recurring_fee_for_usage": 0.0, "reservation_unused_recurring_fee": 0.0,
        "reservation_unused_quantity": 0.0,
        "savings_plan_savings_plan_a_r_n": "", "savings_plan_savings_plan_effective_cost": 0.0,
        "savings_plan_savings_plan_rate": 0.0, "savings_plan_total_commitment_to_date": 0.0,
        "savings_plan_used_commitment": 0.0, "savings_plan_offering_type": "", "savings_plan_purchase_term": "",
    }

NF = {"medium": 2, "large": 4, "xlarge": 8, "xl": 8, "2xlarge": 16, "xlplus": 8}

for d in range(DAYS):
    day = START + timedelta(days=d)
    nxt = day + timedelta(days=1)
    for item in CATALOG:
        for acct in item["accts"]:
            for k in range(n_of(item, acct)):
                q = quantity(item, acct, day, d, k)
                if q is None or q <= 0:
                    continue
                region = item["region"]
                if acct == "acme-data" and item["key"] == "s3_dr":
                    region = "us-east-1"
                tags, team, svc = tags_for(item, acct, k)
                rate = item["rate"]
                cost = round(q * rate, 10)
                r = base_row(acct, day, nxt)
                size = next((p for p in (item["itype"] or "").split(".") if p in NF), "")
                nf = NF.get(size, 0)
                r.update({
                    "identity_line_item_id": h(acct, item["key"], k, day.date(), n=32),
                    "line_item_product_code": item["code"],
                    "line_item_usage_type": f"{REGION_CODE[region]}-{item['ut']}" if region != "global" else item["ut"],
                    "line_item_operation": item["op"],
                    "line_item_availability_zone": f"{region}{'abc'[k % 3]}" if item["az"] else "",
                    "line_item_resource_id": resource_id(item, acct, k, region, team, svc),
                    "line_item_usage_amount": round(q, 6),
                    "line_item_normalization_factor": float(nf),
                    "line_item_normalized_usage_amount": round(q * nf, 6),
                    "line_item_unblended_rate": rate, "line_item_unblended_cost": cost,
                    "line_item_blended_rate": rate, "line_item_blended_cost": cost,
                    "line_item_net_unblended_rate": rate, "line_item_net_unblended_cost": cost,
                    "line_item_line_item_description": f"${rate:g} per {item['unit']} for {item['ut']} in {REGION_NAME[region]}",
                    "pricing_public_on_demand_cost": cost, "pricing_public_on_demand_rate": rate,
                    "pricing_term": "" if item["ut"].startswith("SpotUsage") else "OnDemand",
                    "pricing_unit": item["unit"],
                    "product_product_family": item["fam"], "product_servicecode": item["code"],
                    "product_region_code": "" if region == "global" else region,
                    "product_location": REGION_NAME[region],
                    "product_instance_type": item["itype"] or "",
                    "product_instance_family": "",
                    "product_sku": h(item["code"], item["ut"], region, n=16).upper(),
                    "product": json.dumps({"product_name": item["name"], **item["prod"]}),
                    "resource_tags": json.dumps(tags),
                })
                if item["key"] == "dt_out":
                    r["product_from_location"], r["product_to_location"] = REGION_NAME[region], "External"

                # Compute Savings Plan covers prod EKS nodes
                if item["key"] == "eks_node" and acct == "acme-prod":
                    eff = round(cost * SP_DISCOUNT, 10)
                    r.update({"line_item_line_item_type": "SavingsPlanCoveredUsage",
                              "savings_plan_savings_plan_a_r_n": SP_ARN,
                              "savings_plan_savings_plan_effective_cost": eff,
                              "savings_plan_savings_plan_rate": round(rate * SP_DISCOUNT, 6),
                              "pricing_term": "OnDemand"})
                    rows.append(r)
                    neg = dict(r, identity_line_item_id=h("neg", r["identity_line_item_id"], n=32),
                               line_item_line_item_type="SavingsPlanNegation",
                               line_item_unblended_cost=-cost, line_item_blended_cost=-cost,
                               line_item_net_unblended_cost=-cost,
                               line_item_line_item_description=f"SavingsPlanNegation used by AccountId : {ACCOUNTS[acct][0]} and UsageSku : {r['product_sku']}",
                               savings_plan_savings_plan_effective_cost=0.0)
                    rows.append(neg)
                    continue
                # RDS Reserved Instance covers prod Multi-AZ db (1 of 2 instances)
                if item["key"] == "rds_multiaz" and acct == "acme-prod" and k == 0:
                    r.update({"line_item_line_item_type": "DiscountedUsage",
                              "line_item_unblended_cost": 0.0, "line_item_blended_cost": 0.0,
                              "line_item_net_unblended_cost": 0.0, "line_item_unblended_rate": 0.0,
                              "pricing_term": "Reserved", "pricing_purchase_option": "No Upfront",
                              "reservation_reservation_a_r_n": RI_ARN,
                              "reservation_effective_cost": round(q * RI_EFFECTIVE_RATE, 10),
                              "reservation_recurring_fee_for_usage": round(q * RI_EFFECTIVE_RATE, 10)})
                rows.append(r)

df = pd.DataFrame(rows)

# --------------------------------------------------------------------------- monthly lines
extra = []
months = sorted(df["bill_billing_period_start_date"].unique())
for m in months:
    ps = datetime.strptime(m, "%Y-%m-%dT%H:%M:%SZ")
    _, pe = period_bounds(ps)
    hours = (pe - ps).days * 24
    mdf = df[df.bill_billing_period_start_date == m]

    # Savings Plan recurring fee (payer-purchased, attributed to prod)
    used = mdf.loc[mdf.line_item_line_item_type == "SavingsPlanCoveredUsage", "savings_plan_savings_plan_effective_cost"].sum()
    commit = round(SP_COMMIT_HOURLY * hours, 2)
    r = base_row("acme-prod", ps, pe)
    r.update(identity_line_item_id=h("spfee", m, n=32), line_item_line_item_type="SavingsPlanRecurringFee",
             line_item_product_code="ComputeSavingsPlans", line_item_usage_type="ComputeSP:1yrNoUpfront",
             line_item_usage_amount=float(hours), line_item_unblended_cost=commit, line_item_blended_cost=commit,
             line_item_net_unblended_cost=commit, line_item_unblended_rate=SP_COMMIT_HOURLY,
             line_item_line_item_description="1 year No Upfront Compute Savings Plan",
             savings_plan_savings_plan_a_r_n=SP_ARN, savings_plan_total_commitment_to_date=commit,
             savings_plan_used_commitment=round(min(used, commit), 2), savings_plan_offering_type="ComputeSavingsPlans",
             savings_plan_purchase_term="1yr", pricing_term="Reserved", pricing_purchase_option="No Upfront",
             product=json.dumps({"product_name": "Savings Plans for AWS Compute usage"}))
    extra.append(r)

    # RDS RI monthly fee
    ri_used = mdf.loc[mdf.line_item_line_item_type == "DiscountedUsage", "reservation_effective_cost"].sum()
    ri_fee = round(RI_EFFECTIVE_RATE * hours, 2)
    r = base_row("acme-prod", ps, pe)
    r.update(identity_line_item_id=h("rifee", m, n=32), line_item_line_item_type="RIFee",
             line_item_product_code="AmazonRDS", line_item_usage_type="APS1-HeavyUsage:db.r6g.xl",
             line_item_operation="CreateDBInstance:0014", line_item_usage_amount=float(hours),
             line_item_unblended_cost=ri_fee, line_item_blended_cost=ri_fee, line_item_net_unblended_cost=ri_fee,
             line_item_unblended_rate=RI_EFFECTIVE_RATE,
             line_item_line_item_description="USD 0.69 hourly fee per PostgreSQL, db.r6g.xl Multi-AZ instance",
             reservation_reservation_a_r_n=RI_ARN, reservation_recurring_fee_for_usage=0.0,
             reservation_unused_recurring_fee=round(max(ri_fee - ri_used, 0), 2), pricing_term="Reserved",
             pricing_purchase_option="No Upfront", product_instance_type="db.r6g.xlarge",
             product=json.dumps({"product_name": RDS, "database_engine": "PostgreSQL", "deployment_option": "Multi-AZ"}))
    extra.append(r)

    # Business Support: greater of $100 or 10% of monthly usage (simplified tiering)
    usage_total = mdf.line_item_unblended_cost.sum() + commit + ri_fee
    sup = round(max(100.0, usage_total * 0.10), 2)
    r = base_row("acme-payer", ps, pe)
    r.update(identity_line_item_id=h("support", m, n=32), line_item_line_item_type="Fee",
             line_item_product_code="AWSSupportBusiness", line_item_usage_type="Dollar",
             line_item_unblended_cost=sup, line_item_blended_cost=sup, line_item_net_unblended_cost=sup,
             line_item_line_item_description="AWS Support (Business)",
             product=json.dumps({"product_name": "AWS Support (Business)"}))
    extra.append(r)

    for acct in ACCOUNTS:
        acct_usage = mdf.loc[mdf.line_item_usage_account_name == acct, "line_item_unblended_cost"].sum()
        if acct == "acme-prod":
            acct_usage += commit + ri_fee
        if acct == "acme-payer":
            acct_usage += sup
        tax = round(acct_usage * 0.07, 2)  # Thai VAT 7%
        r = base_row(acct, ps, pe)
        r.update(identity_line_item_id=h("tax", m, acct, n=32), line_item_line_item_type="Tax",
                 line_item_product_code="AWSTax", line_item_tax_type="VAT",
                 line_item_unblended_cost=tax, line_item_blended_cost=tax, line_item_net_unblended_cost=tax,
                 line_item_line_item_description="Tax of type VAT")
        extra.append(r)

    if ps.month == 8:   # promotional credit applied to staging
        r = base_row("acme-staging", ps, pe)
        r.update(identity_line_item_id=h("credit", m, n=32), line_item_line_item_type="Credit",
                 line_item_product_code="AmazonEC2", line_item_unblended_cost=-200.0, line_item_blended_cost=-200.0,
                 line_item_net_unblended_cost=-200.0, line_item_line_item_description="AWS Promotional Credit")
        extra.append(r)
    if ps.month == 9:   # refund for an over-charge on prod
        r = base_row("acme-prod", ps, pe)
        r.update(identity_line_item_id=h("refund", m, n=32), line_item_line_item_type="Refund",
                 line_item_product_code="AmazonCloudFront", line_item_unblended_cost=-35.0,
                 line_item_blended_cost=-35.0, line_item_net_unblended_cost=-35.0,
                 line_item_line_item_description="Refund for CloudFront charges")
        extra.append(r)

df = pd.concat([df, pd.DataFrame(extra)], ignore_index=True)

# --------------------------------------------------------------------------- write
df.to_parquet(f"{args.out}.parquet", index=False)
df.to_csv(f"{args.out}.csv.gz", index=False, compression="gzip")
print(f"rows={len(df):,} cols={df.shape[1]}  {iso(START)[:10]} → {iso(START + timedelta(days=DAYS - 1))[:10]}")
print(df.groupby("line_item_line_item_type")["line_item_unblended_cost"].sum().round(2).to_string())
print(df.groupby("line_item_product_code")["line_item_unblended_cost"].sum().round(2).sort_values(ascending=False).to_string())

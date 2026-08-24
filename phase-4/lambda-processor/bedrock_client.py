import os
import boto3


AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID",
    "amazon.nova-lite-v1:0",
)


bedrock_runtime = boto3.client(
    "bedrock-runtime",
    region_name=AWS_REGION,
)
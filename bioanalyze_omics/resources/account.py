import boto3
import json
from datetime import datetime

import boto3


def get_aws_account_id():
    """
    Get the AWS account ID of the authenticated user.

    Returns:
    - str: The AWS account ID.
    """
    sts_client = boto3.client("sts")
    response = sts_client.get_caller_identity()
    account_id = response["Account"]
    return account_id

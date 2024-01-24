import boto3
import json
from datetime import datetime

from bioanalyze_omics.resources.account import get_aws_account_id


class OmicsIam(object):
    def __init__(self, client=None):
        if client is None:
            self.iam_client = boto3.Session().client("iam")
        else:
            self.iam_client = client

    def get_iam_role_by_name(self, role_name):
        """
        Replace 'YourRoleName' with the actual IAM role name you want to search
        >>> role_name = 'YourRoleName'
        >>> omics_iam = OmicsIam()
        >>> role_info = omics_iam.get_iam_role_by_name(role_name)
        >>>
        >>> if role_info:
        >>>     print(f"IAM Role '{role_name}' found:")
        >>>     print(role_info)
        """
        iam_client = self.iam_client

        try:
            response = iam_client.get_role(RoleName=role_name)
            # If the role is found, 'Role' key will be present in the response
            # return response['Role']
            return response
        except iam_client.exceptions.NoSuchEntityException:
            print(f"IAM role '{role_name}' not found.")
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def get_iam_policy_by_name(self, policy_name):
        """
        Replace 'YourPolicyName' with the actual IAM policy name you want to search

            >>> policy_name = 'YourPolicyName'
            >>> omics_iam = OmicsIam()
            >>> policy_info = omics_iam.get_iam_policy_by_name(policy_name)
            >>>
            >>> if policy_info:
            >>>     print(f"IAM Policy '{policy_name}' found:")
            >>>     print(policy_info)
        """
        iam_client = self.iam_client

        try:
            aws_account_id = get_aws_account_id()
            policy_arn = f"arn:aws:iam::{aws_account_id}:policy/{policy_name}"
            response = iam_client.get_policy(PolicyArn=policy_arn)
            # If the policy is found, 'Policy' key will be present in the response
            return response
        except iam_client.exceptions.NoSuchEntityException:
            print(f"IAM policy '{policy_name}' not found.")
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def create_omics_role(self):
        """
        Create a service IAM role
        To use AWS HealthOmics, you need to create an IAM role that grants the service permissions to access resources in your account. We'll do this below using the IAM client.

        > **Note**: this step is fully automated from the HealthOmics Workflows Console when you create a run
        After creating the role, we next need to add policies to grant permissions. In this case, we are allowing read/write access to all S3 buckets in the account. This is fine for this tutorial, but in a real world setting you will want to scope this down to only the necessary resources. We are also adding a permissions to create CloudWatch Logs which is where any outputs sent to `STDOUT` or `STDERR` are collected.
        """
        dt_fmt = "%Y%m%dT%H%M%S"
        ts = datetime.now().strftime(dt_fmt)
        iam = self.iam_client
        aws_account_id = get_aws_account_id()

        role_name = f"OmicsFullAccessServiceRole"
        role = self.get_iam_role_by_name(role_name)
        if role is None:
            role = iam.create_role(
                # RoleName=f"OmicsServiceRole-{ts}",
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Principal": {"Service": "omics.amazonaws.com"},
                                "Effect": "Allow",
                                "Action": "sts:AssumeRole",
                            }
                        ],
                    }
                ),
                Description="HealthOmics service role",
            )

        s3_policy_name = "OmicsS3FullAccess"
        policy_s3 = self.get_iam_policy_by_name(s3_policy_name)
        if policy_s3 is None:
            policy_s3 = iam.create_policy(
                # PolicyName=f"omics-s3-access-{ts}",
                PolicyName=s3_policy_name,
                PolicyDocument=json.dumps(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "s3:*Object",
                                    "s3:Get*",
                                    "s3:List*",
                                    "s3:*",
                                ],
                                "Resource": ["*"],
                            }
                        ],
                    }
                ),
            )

        logs_policy_name = "OmicsLogsFullAccess"
        policy_logs = self.get_iam_policy_by_name(logs_policy_name)
        if not policy_logs:
            policy_logs = iam.create_policy(
                # PolicyName=f"omics-logs-access-{ts}",
                PolicyName=logs_policy_name,
                PolicyDocument=json.dumps(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": ["logs:CreateLogGroup"],
                                "Resource": [
                                    f"arn:aws:logs:*:{aws_account_id}:log-group:/aws/omics/WorkflowLog:*"
                                ],
                            },
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "logs:DescribeLogStreams",
                                    "logs:CreateLogStream",
                                    "logs:PutLogEvents",
                                ],
                                "Resource": [
                                    f"arn:aws:logs:*:{aws_account_id}:log-group:/aws/omics/WorkflowLog:log-stream:*"
                                ],
                            },
                        ],
                    }
                ),
            )

        for policy in (policy_s3, policy_logs):
            try:
                _ = iam.attach_role_policy(
                    RoleName=role["Role"]["RoleName"], PolicyArn=policy["Policy"]["Arn"]
                )
            except Exception as e:
                print(e)

        return role["Role"]["Arn"]

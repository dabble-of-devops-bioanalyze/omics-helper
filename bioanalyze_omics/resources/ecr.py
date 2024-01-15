import os
import argparse
from glob import glob
import base64
import json
from typing import List, Any, Optional
from os import path
from textwrap import dedent

import boto3
import docker

from bioanalyze_omics.nf import NextflowWorkflow
from bioanalyze_omics.resources.account import get_aws_account_id

import logging
from rich.logging import RichHandler

logging.basicConfig(
    level="INFO",
    format="[ %(name)s ] %(message)s",
    datefmt=None,
    handlers=[RichHandler(rich_tracebacks=True)],
)

log = logging.getLogger("ecr")

"""
Grabbed from here - https://github.com/aws-samples/amazon-omics-tutorials/tree/main/utils

Script to inspect a Nextflow workflow definition and generate resources
to help migrate it to run on AWS HealthOmics.

Specifically designed to handle NF-Core based workflows, but in theory could
handle any Nextflow workflow definition.

What it does:
- look through all *.nf files
- find `container` directives
- extract container uris to:
  - build an image uri manifest
  - create a custom nextflow.config file
"""

POLICY = """{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "omics workflow",
            "Effect": "Allow",
            "Principal": {
                "Service": "omics.amazonaws.com"
            },
            "Action": [
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:BatchCheckLayerAvailability"
            ]
        }
    ]
}"""


def create_ecr_repo(repo_name: str) -> str:
    """
    Create an ECR repository if it doesn't exist.

    Parameters:
    - repo_name (str): The name of the ECR repository to be created.

    Returns:
    - bool: True if the repository was created or already exists, False otherwise.
    """
    # Create an ECR client
    ecr_client = boto3.client("ecr")

    # Check if the repository already exists
    try:
        ecr_client.describe_repositories(repositoryNames=[repo_name])
        log.warning(f"ECR repository '{repo_name}' already exists.")
        return True
    except ecr_client.exceptions.RepositoryNotFoundException:
        # Repository doesn't exist, create it
        try:
            response = ecr_client.create_repository(repositoryName=repo_name)
            log.info(f"ECR repository '{repo_name}' created successfully.")
            return True
        except Exception as e:
            log.fatal(f"Error creating ECR repository '{repo_name}': {e}")
            return False

    return repo_name


# Example usage
# repo_name = 'your-ecr-repo-name'
# create_ecr_repo(repo_name)


def tag_and_push_to_ecr(source_image_uri, ecr_image_uri, ecr_image_tag="latest"):
    # 1. Tag the Docker image with the ECR repository URI
    docker_client = docker.from_env()
    image_tagged = f"{ecr_image_uri}:{ecr_image_tag}"

    try:
        docker_client.images.pull(source_image_uri)
    except Exception as e:
        log.warning(f"Error pulling image: {e}")

    docker_client.images.get(source_image_uri).tag(image_tagged)

    # 2. Authenticate Docker client with ECR
    ecr_client = boto3.client("ecr")
    token = ecr_client.get_authorization_token()
    username, password = (
        base64.b64decode(token["authorizationData"][0]["authorizationToken"])
        .decode()
        .split(":")
    )
    registry = token["authorizationData"][0]["proxyEndpoint"]

    try:
        docker_client.login(
            username,
            password,
            registry=registry,
        )
    except Exception as e:
        log.warning(f"Error authenticating Docker client with ECR. {e}")

    # 3. Push the tagged image to ECR
    try:
        log.info(f"Pushing {image_tagged} to ECR...")
        for line in docker_client.images.push(
            image_tagged,
            stream=True,
            auth_config={"username": username, "password": password},
        ):
            log.info(line.decode("utf-8").strip())
        log.info(f"Image '{image_tagged}' pushed to ECR successfully.")
    except docker.errors.APIError as e:
        log.fatal(f"Error pushing image to ECR: {e}")
        return False
    return True


def apply_omics_ecr_policy(repo_name: str):
    client = boto3.client("ecr")
    try:
        response = client.set_repository_policy(
            repositoryName=repo_name, policyText=POLICY, force=True
        )
    except Exception as e:
        log.warning(f"Unable to apply policy {e}")
    return


def create_ecrs(
    docker_image_names: List[str],
    tag_and_push_file: str,
    aws_region: str = os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
):
    client = boto3.client("ecr")
    with open(tag_and_push_file, "w") as fh:
        fh.write("#!/usr/bin/env bash\n\n")
        for docker_image_name in docker_image_names:
            docker_repo = docker_image_name
            docker_image_name = docker_image_name.replace("quay.io/", "")
            docker_image_name = docker_image_name.replace("docker.io/", "")
            if len(docker_image_name.split(":")) == 1:
                tag = docker_image_name.split(":")[1]
            else:
                tag = "latest"
            docker_image_name = docker_image_name.split(":")[0]
            create_ecr_repo(docker_image_name)
            apply_omics_ecr_policy(docker_image_name)
            account_id = get_aws_account_id()
            ecr_repo_uri = (
                f"{account_id}.dkr.ecr.{aws_region}.amazonaws.com/{docker_image_name}"
            )
            tag_and_push_to_ecr(
                source_image_uri=docker_repo,
                ecr_image_uri=ecr_repo_uri,
                ecr_image_tag=tag,
            )

    return


def append_omics_config(nf_workflow: str):
    file_path = os.path.join(nf_workflow, "nextflow.config")
    log.info("Appending omics.config to nextflow.config. Set --omics=false to disable.")
    omics_content = """// Load omics.config
params.omics = true
if (params.omics) {
    process.debug          = true
    workflow.profile       = 'docker'
    conda.enabled          = false
    docker.enabled         = true
    singularity.enabled    = false
    includeConfig 'omics.config'
}
"""
    try:
        # Open the file in read mode
        with open(file_path, 'r') as file:
            # Read the content of the file
            content = file.read()

        # Check if "HELLO WORLD" is present in the content
        if omics_content not in content:
            # Open the file in append mode and append "HELLO WORLD"
            with open(file_path, 'a') as file:
                file.write(omics_content)
            print("Text appended successfully.")
        else:
            print("Text already present in the file.")

    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")


def inspect_nf(
    aws_region: str,
    aws_profile: str = None,
    output_config_file: str = "omics.config",
    output_manifest_file: str = "container_image_manifest.json",
    nf_workflow: str = os.getcwd(),
    create_ecr: bool = True,
):
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    workflow = NextflowWorkflow(nf_workflow)

    substitutions = None
    # if args.container_substitutions:
    #     with open(args.container_substitutions, 'r') as f:
    #         substitutions = json.load(f)

    namespace_config = None
    # if args.namespace_config:
    #     with open(args.namespace_config, 'r') as f:
    #         namespace_config = json.load(f)

    log.info(f"Creating container image manifest: {output_manifest_file}")
    manifest = workflow.get_container_manifest(substitutions=substitutions)
    with open(output_manifest_file, "w") as file:
        json.dump({"manifest": manifest}, file, indent=4)

    log.info(f"Creating nextflow config file: {output_config_file}")
    config = workflow.get_omics_config(
        session=session, substitutions=substitutions, namespace_config=namespace_config
    )
    with open(output_config_file, "w") as file:
        file.write(config)

    if create_ecr:
        log.info("Creating ECR repositories")
        create_ecrs(
            docker_image_names=manifest,
            tag_and_push_file="tag_and_push.sh",
            aws_region=aws_region,
        )

    append_omics_config(nf_workflow=nf_workflow)
    return

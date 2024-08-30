"""Console script for bioanalyze_omics."""
import sys
import click
import typer

from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated
import os
from bioanalyze_omics.resources import runs, ecr, workflows, iam
from bioanalyze_omics.resources.account import get_aws_account_id

app = typer.Typer()
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


@app.command()
def run_cost(
    run_id: Annotated[str, typer.Option(help="Run ID")],
    aws_region: Annotated[
        str,
        typer.Option(help="AWS Region"),
    ] = AWS_REGION,
    aws_profile: Annotated[str, typer.Option(help="AWS Profile")] = "default",
):
    """
    Calculate the cost of a run. If the run is still running, it will calculate the current cost. If the run is complete, it will calculate the final cost.

    * Cost per task

    * Storage cost

    * Total cost
    """
    runs.calculate_cost(
        run_id=run_id,
        aws_region=aws_region,
        profile=aws_profile,
    )


@app.command()
def create_ecr_repos(
    output_manifest_file: Annotated[
        str,
        typer.Option(
            help="Output manifest file",
        ),
    ] = "container_image_manifest.json",
    output_config_file: Annotated[
        str, typer.Option(help="Output config file")
    ] = "omics.config",
    nf_workflow: Annotated[
        str,
        typer.Option(
            help="Nextflow workflow",
        ),
    ] = os.getcwd(),
    aws_region: Annotated[
        str,
        typer.Option(help="AWS Region"),
    ] = AWS_REGION,
    create_ecr: Annotated[
        bool,
        typer.Option(
            "--create-ecr",
        ),
    ] = True,
):
    """
    Inspect a nextflow workflow and create a manifest file for container images.

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

    - create ECR repos

    - attach omics policies

    - push existing repos
    """
    ecr.inspect_nf(
        aws_region=aws_region,
        output_config_file=output_config_file,
        output_manifest_file=output_manifest_file,
        nf_workflow=nf_workflow,
        create_ecr=create_ecr,
    )
    return


@app.command()
def list_workflows(
    aws_region: Annotated[
        Optional[str],
        typer.Option(help="AWS Region"),
    ] = AWS_REGION,
):
    """List existing omics workflows"""
    omics_workflow = workflows.OmicsWorkflow(aws_region=aws_region)
    omics_workflow.list_workflows()
    return


@app.command()
def list_runs():
    """List existing omics runs"""
    omics_run = runs.OmicsRun()
    omics_run.list_runs()
    return


@app.command()
def create_workflow(
    name: Annotated[
        str,
        typer.Option(help="Nextflow workflow name"),
    ],
    description: Annotated[
        Optional[str],
        typer.Option(help="Nextflow workflow description"),
    ] = None,
    aws_region: Annotated[
        Optional[str],
        typer.Option(
            help="AWS Region",
        ),
    ] = AWS_REGION,
    nf_workflow: Annotated[
        str,
        typer.Option(help="Nextflow workflow directory"),
    ] = os.getcwd(),
):
    """Create an omics workflow from a nextflow workflow directory.

    In order to create the parameters they must be defined in the nextflow_schema.json

    - Parse the nextflow_schema.json and create the parameters

    - Create a zip archive of the workflow directory

    - Upload the zip to AWS Omics workflows
    """
    omics_workflow = workflows.OmicsWorkflow(aws_region=aws_region)
    omics_workflow.create_workflow(
        nextflow_dir=nf_workflow, name=name, description=description
    )
    return


@app.command()
def setup_iam():
    """Setup IAM policies and roles for omics"""
    omics_iam = iam.OmicsIam()
    omics_iam.create_omics_role()
    return


if __name__ == "__main__":
    app()  # pragma: no cover

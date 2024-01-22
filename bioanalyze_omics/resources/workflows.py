import boto3
import time
import argparse
import json
from time import sleep
from datetime import datetime
import glob
import io
import os
from pprint import pprint
from textwrap import dedent
from time import sleep
from urllib.parse import urlparse
from zipfile import ZipFile, ZIP_DEFLATED
from typing import Dict, List, Any
from rich.console import Console
from rich.table import Table

import boto3
import botocore.exceptions
import logging
from rich.logging import RichHandler

logging.basicConfig(
    level="INFO",
    format="[ %(name)s ] %(message)s",
    datefmt=None,
    handlers=[RichHandler(rich_tracebacks=True)],
)

log = logging.getLogger("ecr")


class OmicsWorkflow(object):
    def __init__(self, aws_region="us-east-1", client=None):
        if client is None:
            self.omics_client = boto3.Session(region_name=aws_region).client("omics")
        else:
            self.omics_client = client

    def parse_nextflow_schema(self, nextflow_dir: str) -> Dict:
        """
        parse the nextflow_schema.json and return parameters in the format expected by omics.create_workflow
        :param nextflow_dir:
        :return:
        """
        omics_parameters_definitions = {}
        omics_parameters_defaults = {}
        additional_parameters = """"""
        additional_parameters = [p.strip() for p in additional_parameters.split(",")]

        for param_name in additional_parameters:
            if len(param_name):
                omics_parameters_definitions[param_name] = {
                    "optional": True,
                    "description": param_name,
                }
        omics_parameters_definitions["omics"] = {
            "optional": True,
            "description": "Include omics config.",
            "default": True,
        }

        nextflow_schema = json.loads(
            open(os.path.join(nextflow_dir, "nextflow_schema.json")).read()
        )
        for key in nextflow_schema["definitions"].keys():
            properties = nextflow_schema["definitions"][key]["properties"]
            for param_name in properties.keys():
                omics_parameters_definitions[param_name] = {"optional": True}
                if "description" in properties[param_name]:
                    description = properties[param_name]["description"]
                    description = description.replace("(", " ")
                    description = description.replace(")", " ")
                    description = description.replace("\n", " ")
                    if not len(description):
                        description = param_name
                    omics_parameters_definitions[param_name][
                        "description"
                    ] = description
                if "default" in properties[param_name]:
                    default = properties[param_name]["default"]
                    omics_parameters_defaults[param_name] = default

        return {
            "omics_parameters_definition": omics_parameters_definitions,
            "omics_parameters_defaults": omics_parameters_defaults,
        }

    def create_omics_workflow(
        self,
        workflow_root_dir,
        parameters={"param_name": {"description": "param_desc"}},
        name=None,
        description=None,
        main=None,
    ):
        buffer = io.BytesIO()
        print("creating zip file:")
        with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as zf:
            for file in glob.iglob(
                os.path.join(workflow_root_dir, "**/*"), recursive=True
            ):
                if os.path.isfile(file):
                    arcname = file.replace(os.path.join(workflow_root_dir, ""), "")
                    # print(f".. adding: {file} -> {arcname}")
                    zf.write(file, arcname=arcname)

        response = self.omics_client.create_workflow(
            name=name,
            description=description,
            definitionZip=buffer.getvalue(),  # this argument needs bytes
            main=main,
            parameterTemplate=parameters,
        )

        workflow_id = response["id"]
        log.info(f"Workflow {workflow_id} created, waiting for it to become ACTIVE")

        try:
            waiter = self.omics_client.get_waiter("workflow_active")
            waiter.wait(id=workflow_id)

            print(f"workflow {workflow_id} ready for use")
        except botocore.exceptions.WaiterError as e:
            print(f"workflow {workflow_id} FAILED:")
            print(e)

        workflow = self.omics_client.get_workflow(id=workflow_id)
        return workflow

    def create_workflow(
        self,
        nextflow_dir: str,
        name: str,
        description: str,
        main: str = "main.nf",
    ):
        omics_parameters_definition = self.parse_nextflow_schema(nextflow_dir)
        # omics_parameters_definition.update(extra_parameters_definition)
        workflow = self.create_omics_workflow(
            nextflow_dir,
            parameters=omics_parameters_definition,
            description=description,
            main=main,
            name=name,
        )
        return workflow

    def list_workflows(self):
        response = self.omics_client.list_workflows()
        if "items" not in response:
            return []
        table = Table(title="Workflows")
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("CreationTime")
        for workflow in response["items"]:
            table.add_row(
                workflow["id"],
                workflow["name"],
                workflow["creationTime"].strftime("%Y/%m/%d, %H:%M:%S"),
            )
        console = Console()
        console.print(table)
        return response["items"]

    def submit_workflow(self, workflow_id: str, parameters: Dict[str, Any]):
        response = self.omics_client.submit_workflow(
            id=workflow_id,
            parameterOverrides=parameters,
        )
        return response

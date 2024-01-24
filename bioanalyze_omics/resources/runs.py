import typing
from typing import List, Set, Dict, Tuple, Optional, Any
import boto3
import json
from rich.pretty import pprint
from datetime import datetime
import pandas as pd
import numpy as np

from argparse import ArgumentParser
import os
import json
from typing import Dict, List, Any, TypedDict

import boto3
import requests
from copy import deepcopy
import pandas as pd
from rich.console import Console
from rich.table import Table

MINIMUM_STORAGE_CAPACITY_GIB = 1200
from rich.console import Console
from rich.table import Table

import logging
from rich.logging import RichHandler

logging.basicConfig(
    level="INFO",
    format="[ %(name)s ] %(message)s",
    datefmt=None,
    handlers=[RichHandler(rich_tracebacks=True)],
)

log = logging.getLogger("omics-run")
from bioanalyze_omics.resources import account


class OmicsRunInput(TypedDict):
    output_uri: str
    tags: Dict[str, Any]
    parameters: Dict[str, Any]


def change_case(str: str) -> str:
    res = [str[0].lower()]
    for c in str[1:]:
        if c in ("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
            res.append("_")
            res.append(c.lower())
        else:
            res.append(c)

    return "".join(res)


class OmicsRun(object):
    def __init__(self, client=None):
        if client is None:
            self.omics_client = boto3.Session().client("omics")
        else:
            self.omics_client = client

    def format_run(self, run: Dict, cost: Any) -> Dict:
        run["resourceDigests"] = json.dumps(cost["run"]["resourceDigests"])
        run["tags"] = str(json.dumps(cost["run"]["tags"]))
        run["parameters"] = json.dumps(cost["run"]["parameters"])
        run["logLocation"] = run["logLocation"]["runLogStream"]
        del run["tasks"]
        run_columns = run.keys()
        run_values = run.values()
        formatted_run_columns = [change_case(col) for col in run_columns]
        run = dict(zip(formatted_run_columns, run_values))
        return run

    def get_pricing(self, offering=None):
        if offering:
            # user specified offering
            with open(offering, "r") as file:
                offering = json.load(file)
        else:
            region = self.omics_client.meta.region_name
            response = requests.get(
                f"https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonOmics/current/{region}/index.json"
            )
            if not response.ok:
                response.raise_for_status()

            offering = response.json()

        compute_offering = {
            product[0]: product[1]
            for product in offering["products"].items()
            if product[1]["productFamily"] == "Compute"
        }

        for key in compute_offering:
            offer_term = list(offering["terms"]["OnDemand"][key].values())[0]
            price_dimensions = list(offer_term["priceDimensions"].values())[0]
            compute_offering[key]["priceDimensions"] = price_dimensions

        # set resourceType as the primary hash key
        pricing = {
            instance["attributes"]["resourceType"]: instance
            for instance in compute_offering.values()
            if instance["attributes"].get("resourceType")
        }

        return pricing

    def get_run_info(self, run_id: str):
        client = self.omics_client
        run = client.get_run(id=run_id)

        response = client.list_run_tasks(id=run_id)
        tasks = response["items"]
        while response.get("nextToken"):
            response = client.list_run_tasks(
                id=run_id, startingToken=response.get("nextToken")
            )
            tasks += response["items"]

        tasks_data = []
        for task in tasks:
            new_task = deepcopy(task)
            if "stopTime" in new_task:
                new_task["duration"] = new_task["stopTime"] - new_task["startTime"]
            else:
                new_task["duration"] = (
                    datetime.now(new_task["startTime"].tzinfo) - new_task["startTime"]
                )
            new_task["task"] = new_task["name"].split(":").pop()
            tasks_data.append(new_task)

        run_data = deepcopy(run)
        run_data["tasks"] = tasks_data
        del run_data["ResponseMetadata"]
        if "stopTime" in run_data:
            run_data.update({"duration": run_data["stopTime"] - run_data["startTime"]})
        else:
            run_data.update(
                {"duration": datetime.now(run["startTime"].tzinfo) - run["startTime"]}
            )

        return run_data

    def get_run_cost(
        self,
        run_id,
        storage_gib=MINIMUM_STORAGE_CAPACITY_GIB,
        client=None,
        offering=None,
    ):
        client = self.omics_client

        pricing = self.get_pricing(offering=offering)
        STORAGE_USD_PER_GIB_PER_HR = float(
            pricing["Run Storage"]["priceDimensions"]["pricePerUnit"]["USD"]
        )

        run = self.get_run_info(run_id)
        run_duration_hr = run["duration"].total_seconds() / 3600

        task_costs = []
        for task in run["tasks"]:
            if not task.get("gpus"):
                task["gpus"] = 0
            usd_per_hour = float(
                pricing[task["instanceType"]]["priceDimensions"]["pricePerUnit"]["USD"]
            )
            duration_hr = task["duration"].total_seconds() / 3600
            task_costs += [
                {
                    "id": task["taskId"],
                    "run_id": run_id,
                    "name": task["name"],
                    "status": task["status"],
                    # "resources": {
                    "cpus": task["cpus"],
                    "memory_gib": task["memory"],
                    "gpus": task["gpus"],
                    # },
                    "duration_hr": duration_hr,
                    "instance": task["instanceType"],
                    "usd_per_hour": usd_per_hour,
                    "cost": duration_hr * usd_per_hour,
                    "creation_time": task["creationTime"],
                    "start_time": task["startTime"],
                    "stop_time": task.get("stopTime", None),
                }
            ]

        if not run.get("storageCapacity"):
            # assume the default storage capacity of 1200 GiB
            pass
        else:
            storage_gib = run["storageCapacity"]

        if storage_gib < MINIMUM_STORAGE_CAPACITY_GIB:
            storage_gib = MINIMUM_STORAGE_CAPACITY_GIB

        storage_cost = run_duration_hr * storage_gib * STORAGE_USD_PER_GIB_PER_HR
        total_task_costs = sum([tc["cost"] for tc in task_costs])

        run["total_task_cost"] = total_task_costs
        run["total_storage_cost"] = storage_cost

        return {
            "info": {
                "runId": run["id"],
                "name": run["name"],
                "workflowId": run["workflowId"],
            },
            "run": run,
            "total": storage_cost + total_task_costs,
            "cost_detail": {
                "storage_cost": {
                    "run_id": run["id"],
                    "run_duration_hr": run_duration_hr,
                    "storage_gib": storage_gib,
                    "usd_per_hour": STORAGE_USD_PER_GIB_PER_HR,
                    "cost": storage_cost,
                },
                "total_task_cost": total_task_costs,
                "task_costs": task_costs,
            },
        }

    def gen_tasks_costs_df(self, cost: Any) -> pd.DataFrame:
        task_costs_df = pd.DataFrame.from_records(cost["cost_detail"]["task_costs"])
        return task_costs_df

    def gen_storage_costs_df(self, cost: Any) -> pd.DataFrame:
        storage_costs_df = pd.DataFrame.from_records(
            [cost["cost_detail"]["storage_cost"]]
        )
        return storage_costs_df

    def gen_run_df(self, run: Any) -> pd.DataFrame:
        run_df = pd.DataFrame.from_records([run])
        return run_df

    def list_runs(self):
        response = self.omics_client.list_runs()
        if "items" not in response:
            return []
        table = Table(title="Runs")
        table.add_column("RunId")
        table.add_column("WorkflowId")
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("CreationTime")
        table.add_column("StartTime")
        table.add_column("StopTime")
        for run in response["items"]:
            table.add_row(
                run["id"],
                run["workflowId"],
                run["name"],
                run["status"],
                run["creationTime"].strftime("%Y/%m/%d, %H:%M:%S"),
                run["startTime"].strftime("%Y/%m/%d, %H:%M:%S"),
                run["stopTime"].strftime("%Y/%m/%d, %H:%M:%S"),
            )
        console = Console()
        console.print(table)
        return response["items"]

    def start_run(
        self,
        output_uri: str,
        workflow_id: str,
        run_name: str,
        storage_capacity: int = 9600,
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, Any]] = None,
        role_arn: Optional[str] = None,
        run_group_id: Optional[str] = None,
    ):
        omics = self.omics_client
        aws_account_id = account.get_aws_account_id()
        if not role_arn:
            role_arn = f"arn:aws:iam::{aws_account_id}:role/OmicsFullAccessServiceRole"
            log.info(f"No role_arn provided, using default role: {role_arn}")
        if not tags:
            tags = {}

        dt_fmt = "%Y%m%dT%H%M%S"
        ts = datetime.now().strftime(dt_fmt)
        try:
            run = omics.start_run(
                workflowId=workflow_id,
                name=run_name,
                roleArn=role_arn,
                parameters=parameters,
                outputUri=output_uri,
                # runGroupId=run_group_id,
                tags=tags,
                storageCapacity=storage_capacity,
                logLevel="ALL",
            )

            log.info(
                f"""
Submitted
Run        : {run['id']}
WorkflowId : {workflow_id}
RunGroupId : {run_group_id}
Tags       : {tags}
Parameters : {parameters}
            """
            )

            return run
        except Exception as e:
            log.error(e)
            raise


def calculate_cost(
    run_id: str,
    offering: str = None,
    profile: str = None,
    aws_region: str = os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
):
    session = boto3.Session(
        region_name=aws_region,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", None),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", None),
    )
    omics_runs = OmicsRun(client=session.client("omics"))
    cost = omics_runs.get_run_cost(
        run_id, client=session.client("omics"), offering=offering
    )
    task_costs_df = pd.DataFrame.from_records(cost["cost_detail"]["task_costs"])
    storage_costs_df = pd.DataFrame.from_records([cost["cost_detail"]["storage_cost"]])
    total_task_cost = cost["cost_detail"]["total_task_cost"]
    total_storage_cost = cost["cost_detail"]["storage_cost"]["cost"]
    run = cost["run"]
    run = omics_runs.format_run(run, cost)
    run_df = pd.DataFrame.from_records([run])

    # print(json.dumps(cost, indent=4, default=str))
    pprint(cost, expand_all=True)
    return cost

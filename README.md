# BioAnalyze Omics

Helper utils for omics

* Free software: MIT license

## Usage

### Prepare the workflow

In order to use a nextflow workflow with AWS Omics, you need to prepare it first.

* All images must be stored in *your* ecr repository. You can use the `create-ecr-repos` command to create the repos and
  push the images.
* All parameters must be defined in the `nextflow_schema.json` file. You can use the `create-workflow` command to create
  the workflow.
* The workflow must be zipped and uploaded to AWS Omics. You can use the `create-workflow` command to create the
  workflow.

```bash
omicsx create-ecr-repos --nf-workflow <your-nextflow-workflow-directory> \
  --aws-region <your-aws-region>

omicsx create-workflow --nf-workflow <your-nextflow-workflow-directory> \
  --name <your-workflow-name> \
  --aws-region <your-aws-region>
```

# CLI

**Usage**:

```console
$ omicsx --help
```

**Options**:

* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `create-ecr-repos`: Inspect a nextflow workflow and create a...
* `create-workflow`: Create an omics workflow from a nextflow...
* `run-cost`: Calculate the cost of a run.

## `create-ecr-repos`

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

**Usage**:

```console
$ omicsx create-ecr-repos [OPTIONS] OUTPUT_MANIFEST_FILE OUTPUT_CONFIG_FILE NF_WORKFLOW
```

**Arguments**:

* `OUTPUT_MANIFEST_FILE`: [required]
* `OUTPUT_CONFIG_FILE`: [required]
* `NF_WORKFLOW`: [required]

**Options**:

* `--aws-region TEXT`: [default: us-east-1]
* `--aws-profile TEXT`: [default: default]
* `--create-ecr / --no-create-ecr`: [default: create-ecr]
* `--help`: Show this message and exit.

## `create-workflow`

Create an omics workflow from a nextflow workflow directory.

In order to create the parameters they must be defined in the nextflow_schema.json

- Parse the nextflow_schema.json and create the parameters
- Create a zip archive of the workflow directory
- Upload the zip to AWS Omics workflows

**Usage**:

```console
$ omicsx create-workflow [OPTIONS] NF_WORKFLOW NAME
```

**Arguments**:

* `NF_WORKFLOW`: [required]
* `NAME`: [required]

**Options**:

* `--description TEXT`
* `--aws-region TEXT`: [default: us-east-1]
* `--aws-profile TEXT`: [default: default]
* `--help`: Show this message and exit.

## `list-workflows`

List existing omics workflows

**Options**:

* `--aws-region TEXT`: [default: us-east-1]
* `--aws-profile TEXT`: [default: default]
* `--help`: Show this message and exit.

## `list-runs`

List existing omics runs

**Usage**:

```console
$ list-runs [OPTIONS]
```

**Options**:

* `--aws-region TEXT`: [default: us-east-1]
* `--aws-profile TEXT`: [default: default]
* `--help`: Show this message and exit.

## `run-cost`

Calculate the cost of a run. If the run is still running, it will calculate the current cost. If the run is complete, it
will calculate the final cost.

* Cost per task

* Storage cost

* Total cost

**Usage**:

```console
$ run-cost [OPTIONS] RUN_ID
```

**Arguments**:

* `RUN_ID`: [required]

**Options**:

* `--aws-region TEXT`: [default: us-east-1]
* `--aws-profile TEXT`: [default: default]
* `--help`: Show this message and exit.

## Credits

* [AWS Omics Utils](https://github.com/aws-samples/amazon-omics-tutorials/tree/main/utils/scripts)
* [Cookiecutter]( https://github.com/audreyr/cookiecutter)
* [audreyr/cookiecutter-pypackage](https://github.com/audreyr/cookiecutter-pypackage)

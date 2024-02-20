#!/usr/bin/env python


import pandas as pd
import os

s3_path = "s3://bioanalyze-omics-dev/reference/nf-core/test-datasets/rnaseq/"
df = pd.read_csv(
    "https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq/samplesheet/v3.10/samplesheet_test.csv"
)

fastq_1s = []
fastq_2s = []
os.makedirs("data", exist_ok=True)
os.chdir("data")
for fastq_1, fastq_2 in zip(df["fastq_1"].tolist(), df["fastq_2"].tolist()):
    if isinstance(fastq_1, str):
        print(fastq_1)
        if not os.path.exists(os.path.basename(fastq_1)):
            os.system(f"wget {fastq_1}")
        fastq_1 = os.path.basename(fastq_1)
        os.system(f"aws s3 cp {fastq_1} {s3_path}")
        fastq_1s.append(f"{s3_path}{fastq_1}")
    else:
        fastq_1s.append(None)

    if isinstance(fastq_2, str):
        print(fastq_2)
        if not os.path.exists(os.path.basename(fastq_2)):
            os.system(f"wget {fastq_2}")
        fastq_2 = os.path.basename(fastq_2)
        os.system(f"aws s3 cp {fastq_1} {s3_path}")
        fastq_2s.append(f"{s3_path}{fastq_2}")
    else:
        fastq_2s.append(None)

df['fastq_1'] = fastq_1s
df['fastq_2'] = fastq_2s
df.to_csv("samplesheet-omics.csv", index=False)

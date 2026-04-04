from pyspark.sql import functions as F


def transform(src_profile_stage, src_profile_history):
    audit_cols = src_profile_history.select("ProfileIdentifier")
    return (
        src_profile_stage.alias("base")
        .join(audit_cols.alias("audit"), on="ProfileIdentifier", how="left")
        .select("ProfileIdentifier")
    )

from pyspark.sql import functions as F


def transform(src_profile_stage, src_profile_history):
    audit_cols = src_profile_history.select("profile_key", "reviewed_on")
    return (
        src_profile_stage.alias("base")
        .join(audit_cols.alias("audit"), on="profile_key", how="left")
        .select("profile_key", F.col("audit.reviewed_on").alias("reviewed_on"))
    )

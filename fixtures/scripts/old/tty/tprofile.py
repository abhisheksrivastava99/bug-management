from pyspark.sql import functions as F


def transform(src_profile_base, src_profile_audit):
    audit_cols = src_profile_audit.select("profile_id", "last_reviewed")
    return (
        src_profile_base.alias("base")
        .join(audit_cols.alias("audit"), on="profile_id", how="left")
        .select("profile_id", F.col("audit.last_reviewed").alias("last_reviewed"))
    )

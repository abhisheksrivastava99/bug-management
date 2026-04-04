from pyspark.sql import functions as F


def transform(src_profile_base, src_profile_audit):
    audit_cols = src_profile_audit.select("ProfileIdentifier")
    return (
        src_profile_base.alias("base")
        .join(audit_cols.alias("audit"), on="ProfileIdentifier", how="left")
        .select("ProfileIdentifier")
    )

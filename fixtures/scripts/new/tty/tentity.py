from pyspark.sql import functions as F


def transform(src_tentity_base, src_tentity_audit):
    audit_snapshot = src_tentity_audit.select(
        "EntityIdentifier",
        "UpdatedByUser",
    )

    return (
        src_tentity_base.alias("base")
        .join(audit_snapshot.alias("audit"), on="EntityIdentifier", how="left")
        .select(
            F.col("base.EntityIdentifier").alias("EntityIdentifier"),
            F.col("base.EntityDisplayName").alias("EntityDisplayName"),
            F.col("audit.UpdatedByUser").alias("UpdatedByUser"),
        )
    )

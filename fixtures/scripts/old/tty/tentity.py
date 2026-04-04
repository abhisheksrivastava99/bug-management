from pyspark.sql import functions as F


def transform(src_tentity_base, src_tentity_audit):
    audit_snapshot = src_tentity_audit.select(
        "entity_id",
        "date_updated",
        "updated_by",
    )

    return (
        src_tentity_base.alias("base")
        .join(audit_snapshot.alias("audit"), on="entity_id", how="left")
        .select(
            F.col("base.entity_id").alias("entity_id"),
            F.col("base.entity_name").alias("entity_name"),
            F.col("audit.date_updated").alias("date_updated"),
            F.col("audit.updated_by").alias("updated_by"),
        )
    )

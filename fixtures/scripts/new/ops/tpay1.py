from pyspark.sql import functions as F


def transform(src_pay_base, src_pay_audit):
    audit_latest = src_pay_audit.select(
        "entity_id",
        "updated_by",
    )

    return (
        src_pay_base.alias("base")
        .join(audit_latest.alias("audit"), on="entity_id", how="left")
        .select(
            F.col("base.entity_id").alias("entity_id"),
            F.col("base.entity_name").alias("entity_name"),
            F.col("audit.updated_by").alias("updated_by"),
        )
    )

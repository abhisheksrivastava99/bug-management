from pyspark.sql import functions as F


def transform(src_inv_base, src_inv_audit):
    return (
        src_inv_base.alias("base")
        .join(src_inv_audit.alias("audit"), on="entity_id", how="left")
        .select("entity_id", F.col("audit.inv_metric").alias("inv_metric_alt"))
    )

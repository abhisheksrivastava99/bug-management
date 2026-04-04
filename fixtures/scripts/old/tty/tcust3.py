from pyspark.sql import functions as F


def transform(src_cust_base, src_cust_audit):
    return (
        src_cust_base.alias("base")
        .join(src_cust_audit.alias("audit"), on="entity_id", how="left")
        .withColumn("cust_metric", F.col("base.metric_a") + F.col("audit.metric_b"))
        .select("entity_id", "cust_metric")
    )

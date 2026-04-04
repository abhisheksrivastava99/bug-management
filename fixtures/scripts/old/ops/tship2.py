from pyspark.sql import functions as F


def transform(src_ship_base, src_ship_audit):
    return (
        src_ship_base.alias("base")
        .join(src_ship_audit.alias("audit"), on="entity_id", how="left")
        .select("entity_id", F.col("audit.ship_metric").alias("ship_metric"))
    )

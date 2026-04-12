from pyspark.sql import functions as F


def transform(src_orderlink_base, src_orderlink_status):
    return (
        src_orderlink_base.alias("header")
        .join(src_orderlink_status.alias("status"), on="order_id", how="left")
        .select("order_id", F.col("status.settlement_flag").alias("settlement_flag"))
    )

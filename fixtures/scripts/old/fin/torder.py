from pyspark.sql import functions as F


def transform(src_order_header, src_order_status):
    return (
        src_order_header.alias("header")
        .join(src_order_status.alias("status"), on="order_id", how="left")
        .select("order_id", F.col("status.settlement_flag").alias("settlement_flag"))
    )

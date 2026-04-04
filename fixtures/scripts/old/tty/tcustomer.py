from pyspark.sql import functions as F


def transform(src_customer_master, src_customer_status):
    return (
        src_customer_master.alias("master")
        .join(src_customer_status.alias("status"), on="customer_id", how="left")
        .select(
            F.col("master.customer_id").alias("customer_id"),
            F.col("master.customer_name").alias("customer_name"),
            F.col("status.status_cd").alias("status_cd"),
        )
    )

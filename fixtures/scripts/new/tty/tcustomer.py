from pyspark.sql import functions as F


def transform(src_customer_master, src_customer_status):
    return (
        src_customer_master.alias("master")
        .join(src_customer_status.alias("status"), on="CustomerIdentifier", how="left")
        .select(
            F.col("master.CustomerIdentifier").alias("CustomerIdentifier"),
            F.col("master.CustomerDisplayName").alias("CustomerDisplayName"),
            F.col("status.CustomerStatusSourceCode").alias("customer_status_label"),
        )
    )

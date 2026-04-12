from pyspark.sql import functions as F


def transform(src_dup_shipment_base, src_dup_shipment_status):
    return (
        src_dup_shipment_base.alias("master")
        .join(src_dup_shipment_status.alias("status"), on="shipment_id", how="left")
        .select(
            F.col("master.shipment_id").alias("shipment_id"),
            F.col("status.shipment_status").alias("shipment_status"),
        )
    )

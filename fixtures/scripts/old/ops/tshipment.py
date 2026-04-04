from pyspark.sql import functions as F


def transform(src_shipment_base, src_shipment_status):
    return (
        src_shipment_base.alias("master")
        .join(src_shipment_status.alias("status"), on="shipment_id", how="left")
        .select(
            F.col("master.shipment_id").alias("shipment_id"),
            F.col("status.shpmnt_status").alias("shpmnt_status"),
        )
    )

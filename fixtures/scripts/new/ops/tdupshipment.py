from pyspark.sql import functions as F


def transform(src_dup_shipment_base, src_dup_shipment_status):
    return (
        src_dup_shipment_base.alias("base")
        .join(src_dup_shipment_status.alias("status"), on="ShipmentIdentifier", how="left")
        .select(
            F.col("base.ShipmentIdentifier").alias("ShipmentIdentifier"),
            F.col("status.ShipmentStatusSourceCode").alias("ShipmentStatus"),
        )
    )

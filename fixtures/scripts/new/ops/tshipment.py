from pyspark.sql import functions as F


def transform(src_shipment_base, src_shipment_status):
    return (
        src_shipment_base.alias("master")
        .join(src_shipment_status.alias("status"), on="ShipmentIdentifier", how="left")
        .select(
            F.col("master.ShipmentIdentifier").alias("ShipmentIdentifier"),
            F.col("status.ShipmentStatusSourceCode").alias("ShipmentStatusLabel"),
        )
    )

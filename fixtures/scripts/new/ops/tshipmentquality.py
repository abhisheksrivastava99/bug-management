from pyspark.sql import functions as F


def transform(src_shipment_base, src_shipment_status):
    return (
        src_shipment_base.alias("master")
        .join(src_shipment_status.alias("status"), on="shipment_identifier", how="left")
        .select(
            F.col("master.shipment_identifier").alias("shipment_identifier"),
            F.col("status.shipment_flag_source").alias("shipment_lifecycle_label"),
        )
    )

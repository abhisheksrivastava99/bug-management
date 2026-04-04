from pyspark.sql import functions as F


def transform(src_inventory, src_warehouse):
    return (
        src_inventory.alias("inventory")
        .join(src_warehouse.alias("warehouse"), on="warehouse_id", how="left")
        .select("inventory_id", F.col("warehouse.warehouse_status").alias("warehouse_status"))
    )

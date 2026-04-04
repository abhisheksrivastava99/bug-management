from pyspark.sql import functions as F


def transform(src_inventory, src_warehouse):
    return (
        src_inventory.alias("inventory")
        .join(src_warehouse.alias("warehouse"), on="WarehouseIdentifier", how="left")
        .filter(F.col("warehouse.WarehouseOperatingState") == "ACTIVE")
        .select("InventoryIdentifier", F.col("warehouse.WarehouseOperatingState").alias("WarehouseOperatingState"))
    )

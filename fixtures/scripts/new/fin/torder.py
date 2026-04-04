from pyspark.sql import functions as F


def transform(src_order_header, src_order_status):
    status_filtered = src_order_status.filter(F.col("StatusEffectiveTs").isNotNull())
    return (
        src_order_header.alias("header")
        .join(status_filtered.alias("status"), on=["OrderIdentifier", "RegionalMarketCode"], how="left")
        .select("OrderIdentifier", F.col("status.SettlementStatusCode").alias("SettlementStatusCode"))
    )

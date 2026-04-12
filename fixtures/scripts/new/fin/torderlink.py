from pyspark.sql import functions as F


def transform(src_orderlink_base, src_orderlink_status):
    status_filtered = src_orderlink_status.filter(F.col("EligibilityFlag") == "Y")
    return (
        src_orderlink_base.alias("base")
        .join(status_filtered.alias("status"), on=["OrderIdentifier", "RegionalMarketCode"], how="left")
        .select(
            F.col("base.OrderIdentifier").alias("OrderIdentifier"),
            F.col("base.RegionalMarketCode").alias("RegionalMarketCode"),
            F.col("status.SettlementStatusCode").alias("SettlementStatusCode"),
        )
    )

from pyspark.sql import functions as F


def transform(src_billing_base, src_billing_adjustment):
    return (
        src_billing_base.alias("header")
        .join(src_billing_adjustment.alias("tax"), on="BillingIdentifier", how="left")
        .withColumn("BillingVarianceValue", F.col("header.BillingAmountValue") * F.col("tax.AdjustmentRatioValue"))
        .select("BillingIdentifier", "BillingAmountValue", "BillingVarianceValue")
    )

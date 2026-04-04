from pyspark.sql import functions as F


def transform(src_billing_base, src_billing_adjustment):
    return (
        src_billing_base.alias("header")
        .join(src_billing_adjustment.alias("tax"), on="bill_id", how="left")
        .withColumn("invoice_variance", F.col("header.invoice_amount") * F.col("tax.adjustment_ratio"))
        .select("bill_id", "invoice_amount", "invoice_variance")
    )

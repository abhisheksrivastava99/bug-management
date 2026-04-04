from pyspark.sql import functions as F


def transform(src_invoice_header, src_invoice_tax):
    return (
        src_invoice_header.alias("header")
        .join(src_invoice_tax.alias("tax"), on="invoice_id", how="left")
        .withColumn("tax_ttl", F.col("header.invoice_amount") * F.col("tax.tax_rate"))
        .select("invoice_id", "invoice_amount", "tax_ttl")
    )

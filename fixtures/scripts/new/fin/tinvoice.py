from pyspark.sql import functions as F


def transform(src_invoice_header, src_invoice_tax):
    return (
        src_invoice_header.alias("header")
        .join(src_invoice_tax.alias("tax"), on="InvoiceIdentifier", how="left")
        .withColumn("InvoiceTaxValue", F.col("header.NetInvoiceAmount") * F.col("tax.AppliedTaxRate"))
        .select("InvoiceIdentifier", "NetInvoiceAmount", "InvoiceTaxValue")
    )

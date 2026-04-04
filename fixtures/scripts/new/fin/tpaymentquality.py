from pyspark.sql import functions as F


def transform(src_payment_base, src_payment_audit):
    audit_snapshot = src_payment_audit.select(
        "PaymentIdentifier",
        "ScoreUpdatedByUser",
    )

    return (
        src_payment_base.alias("base")
        .join(audit_snapshot.alias("audit"), on="PaymentIdentifier", how="left")
        .select(
            F.col("base.PaymentIdentifier").alias("PaymentIdentifier"),
            F.col("base.PaymentCategoryName").alias("PaymentCategoryName"),
            F.col("audit.ScoreUpdatedByUser").alias("ScoreUpdatedByUser"),
        )
    )

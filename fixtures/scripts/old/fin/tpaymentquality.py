from pyspark.sql import functions as F


def transform(src_payment_base, src_payment_audit):
    audit_snapshot = src_payment_audit.select(
        "payment_id",
        "payment_score",
        "score_updated_by",
    )

    return (
        src_payment_base.alias("base")
        .join(audit_snapshot.alias("audit"), on="payment_id", how="left")
        .select(
            F.col("base.payment_id").alias("payment_id"),
            F.col("base.payment_category").alias("payment_category"),
            F.col("audit.payment_score").alias("payment_score"),
            F.col("audit.score_updated_by").alias("score_updated_by"),
        )
    )

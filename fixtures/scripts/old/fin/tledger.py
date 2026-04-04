from pyspark.sql import functions as F


def transform(src_ledger_header, src_ledger_status):
    return (
        src_ledger_header.alias("master")
        .join(src_ledger_status.alias("status"), on="ledger_id", how="left")
        .select(
            F.col("master.ledger_id").alias("ledger_id"),
            F.col("status.legacy_flag").alias("legacy_flag"),
        )
    )

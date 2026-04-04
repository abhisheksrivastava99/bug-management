from pyspark.sql import functions as F


def transform(src_ledger_header, src_ledger_status):
    return (
        src_ledger_header.alias("master")
        .join(src_ledger_status.alias("status"), on="LedgerIdentifier", how="left")
        .select(
            F.col("master.LedgerIdentifier").alias("LedgerIdentifier"),
            F.col("status.LedgerStatusSourceCode").alias("LedgerMigrationStatusText"),
        )
    )

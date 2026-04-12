from pyspark.sql import functions as F


def transform(src_eventlog_base, src_eventlog_audit):
    audit_cols = src_eventlog_audit.select("EventIdentifier", "RawEventOccurredTs")
    return (
        src_eventlog_base.alias("base")
        .join(audit_cols.alias("audit"), on="EventIdentifier", how="left")
        .select(
            F.col("base.EventIdentifier").alias("EventIdentifier"),
            F.col("audit.RawEventOccurredTs").alias("EventOccurredTs"),
        )
    )

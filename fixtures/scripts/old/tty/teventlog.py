from pyspark.sql import functions as F


def transform(src_eventlog_base, src_eventlog_audit):
    audit_cols = src_eventlog_audit.select("event_id", "occurred_ts")
    return (
        src_eventlog_base.alias("base")
        .join(audit_cols.alias("audit"), on="event_id", how="left")
        .select("event_id", F.col("audit.occurred_ts").alias("occurred_ts"))
    )

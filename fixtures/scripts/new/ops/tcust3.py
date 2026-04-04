from pyspark.sql import functions as F


def transform(src_cust_base, src_cust_audit):
    return (
        src_cust_base.alias("base")
        .join(src_cust_audit.alias("audit"), on="entity_id", how="left")
        .select("entity_id")
    )

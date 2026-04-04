from pyspark.sql import functions as F


def transform(src_balance_header, src_balance_snapshot):
    return src_balance_header.select("balance_id", "balance_amount")

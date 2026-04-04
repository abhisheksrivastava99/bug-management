import json
import random
from pathlib import Path
from typing import Dict, List


def get_all_scenarios(seed: int = 11) -> List[Dict]:
    scenarios = _curated_scenarios()
    scenarios.extend(_generated_scenarios(seed))
    return scenarios


def build_scenario_catalog(seed: int = 11) -> Dict:
    scenarios = get_all_scenarios(seed)
    return {
        "seed": seed,
        "golden_scenarios": [scenario["id"] for scenario in scenarios if scenario["golden"]],
        "scenarios": scenarios,
    }


def write_catalog_json(path: Path, seed: int = 11) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_scenario_catalog(seed), indent=2), encoding="utf-8")


def _curated_scenarios() -> List[Dict]:
    return [
        _scenario(
            scenario_id="tty_tentity_missing_final_select",
            golden=True,
            scenario_type="missing_final_select",
            division="TTY",
            table_name="TENTITY",
            source_tables=["src_tentity_base", "src_tentity_audit"],
            owner_users=["tty_owner", "data_support_tty"],
            support_team="data_team_tty",
            business_description="Core entity master data for the TTY division.",
            criticality="high",
            issue_title="TTY_TENTITY_Column UPDATEDDATE missing",
            focus_columns=["UPDATEDDATE"],
            root_cause_family="missing_final_select",
            decision="regression_detected",
            expected_keywords=["date_updated", "UPDATEDDATE", "not projected"],
            mapping_rows=[
                _mapping("tentity_old", "tentity_new", "entity_id", "EntityIdentifier"),
                _mapping("tentity_old", "tentity_new", "entity_name", "EntityDisplayName"),
                _mapping("tentity_old", "tentity_new", "date_updated", "UPDATEDDATE"),
                _mapping("tentity_old", "tentity_new", "updated_by", "UpdatedByUser"),
            ],
            old_script=_old_projection_script(
                ["src_tentity_base", "src_tentity_audit"],
                join_key="entity_id",
                id_column="entity_id",
                name_column="entity_name",
                focus_column="date_updated",
                aux_column="updated_by",
            ),
            new_script=_new_projection_script_missing(
                ["src_tentity_base", "src_tentity_audit"],
                join_key="EntityIdentifier",
                id_column="EntityIdentifier",
                name_column="EntityDisplayName",
                focus_column="UPDATEDDATE",
                aux_column="UpdatedByUser",
            ),
        ),
        _scenario(
            scenario_id="tty_tcustomer_wrong_new_alias",
            golden=True,
            scenario_type="alias_mismatch",
            division="TTY",
            table_name="TCUSTOMER",
            source_tables=["src_customer_master", "src_customer_status"],
            owner_users=["customer_owner", "data_support_tty"],
            support_team="data_team_tty",
            business_description="TTY customer dimension and lifecycle attributes.",
            criticality="medium",
            issue_title="TTY_TCUSTOMER_Column customer_status_code missing in Gavin3 output",
            focus_columns=["customer_status_code"],
            root_cause_family="alias_mismatch",
            decision="regression_detected",
            expected_keywords=["status_cd", "customer_status_code", "customer_status_label"],
            mapping_rows=[
                _mapping("tcustomer_old", "tcustomer_new", "customer_id", "CustomerIdentifier"),
                _mapping("tcustomer_old", "tcustomer_new", "customer_name", "CustomerDisplayName"),
                _mapping("tcustomer_old", "tcustomer_new", "status_cd", "customer_status_code"),
            ],
            old_script=_old_alias_script(
                ["src_customer_master", "src_customer_status"],
                join_key="customer_id",
                id_column="customer_id",
                focus_column="status_cd",
                companion_column="customer_name",
            ),
            new_script=_new_alias_mismatch_script(
                ["src_customer_master", "src_customer_status"],
                join_key="CustomerIdentifier",
                id_column="CustomerIdentifier",
                source_column="CustomerStatusSourceCode",
                expected_column="customer_status_code",
                wrong_column="customer_status_label",
                companion_column="CustomerDisplayName",
            ),
        ),
        _scenario(
            scenario_id="fin_tinvoice_renamed_derivation",
            golden=True,
            scenario_type="renamed_derivation",
            division="FIN",
            table_name="TINVOICE",
            source_tables=["src_invoice_header", "src_invoice_tax"],
            owner_users=["fin_owner", "data_support_fin"],
            support_team="data_team_fin",
            business_description="Invoice fact table with derived tax totals.",
            criticality="high",
            issue_title="FIN_TINVOICE_Column TotalTax missing",
            focus_columns=["TotalTax"],
            root_cause_family="renamed_derivation",
            decision="regression_detected",
            expected_keywords=["tax_ttl", "TotalTax", "InvoiceTaxValue"],
            mapping_rows=[
                _mapping("tinvoice_old", "tinvoice_new", "invoice_id", "InvoiceIdentifier"),
                _mapping("tinvoice_old", "tinvoice_new", "invoice_amount", "NetInvoiceAmount"),
                _mapping("tinvoice_old", "tinvoice_new", "tax_ttl", "TotalTax"),
            ],
            old_script=_old_derivation_script(
                ["src_invoice_header", "src_invoice_tax"],
                join_key="invoice_id",
                amount_column="invoice_amount",
                rate_column="tax_rate",
                derived_column="tax_ttl",
            ),
            new_script=_new_derivation_script_wrong(
                ["src_invoice_header", "src_invoice_tax"],
                join_key="InvoiceIdentifier",
                amount_column="NetInvoiceAmount",
                rate_column="AppliedTaxRate",
                expected_column="TotalTax",
                wrong_column="InvoiceTaxValue",
            ),
        ),
        _scenario(
            scenario_id="fin_torder_join_null_spike",
            golden=True,
            scenario_type="join_null_spike",
            division="FIN",
            table_name="TORDER",
            source_tables=["src_order_header", "src_order_status"],
            owner_users=["fin_order_owner", "data_support_fin"],
            support_team="data_team_fin",
            business_description="Financial orders and settlement status.",
            criticality="high",
            issue_title="FIN_TORDER_Column SettlementStatusCode mostly null after migration",
            focus_columns=["SettlementStatusCode"],
            root_cause_family="join_null_spike",
            decision="investigate_join_logic",
            expected_keywords=["settlement_flag", "SettlementStatusCode", "join"],
            mapping_rows=[
                _mapping("torder_old", "torder_new", "order_id", "OrderIdentifier"),
                _mapping("torder_old", "torder_new", "region_code", "RegionalMarketCode"),
                _mapping("torder_old", "torder_new", "settlement_flag", "SettlementStatusCode"),
            ],
            old_script=_old_join_script(
                ["src_order_header", "src_order_status"],
                join_key="order_id",
                focus_column="settlement_flag",
            ),
            new_script=_new_join_script(
                ["src_order_header", "src_order_status"],
                join_keys=["OrderIdentifier", "RegionalMarketCode"],
                focus_column="SettlementStatusCode",
                filter_column="StatusEffectiveTs",
            ),
        ),
        _scenario(
            scenario_id="ops_tinventory_filter_row_loss",
            golden=True,
            scenario_type="filter_row_loss",
            division="OPS",
            table_name="TINVENTORY",
            source_tables=["src_inventory", "src_warehouse"],
            owner_users=["inventory_owner", "data_support_ops"],
            support_team="data_team_ops",
            business_description="Inventory balance and warehouse status table.",
            criticality="medium",
            issue_title="OPS_TINVENTORY_Column WarehouseOperatingState row count dropped after filter",
            focus_columns=["WarehouseOperatingState"],
            root_cause_family="filter_row_loss",
            decision="investigate_filter_logic",
            expected_keywords=["warehouse_status", "WarehouseOperatingState", "filter"],
            mapping_rows=[
                _mapping("tinventory_old", "tinventory_new", "inventory_id", "InventoryIdentifier"),
                _mapping("tinventory_old", "tinventory_new", "warehouse_status", "WarehouseOperatingState"),
            ],
            old_script=_old_filter_script(
                ["src_inventory", "src_warehouse"],
                join_key="warehouse_id",
                id_column="inventory_id",
                focus_column="warehouse_status",
            ),
            new_script=_new_filter_script(
                ["src_inventory", "src_warehouse"],
                join_key="WarehouseIdentifier",
                id_column="InventoryIdentifier",
                focus_column="WarehouseOperatingState",
            ),
        ),
        _scenario(
            scenario_id="tty_tprofile_source_column_disappearance",
            golden=True,
            scenario_type="source_column_disappearance",
            division="TTY",
            table_name="TPROFILE",
            source_tables=["src_profile_base", "src_profile_audit"],
            owner_users=["profile_owner", "data_support_tty"],
            support_team="data_team_tty",
            business_description="Profile dimension with audit attributes.",
            criticality="medium",
            issue_title="TTY_TPROFILE_Column ProfileReviewCompletedTs missing",
            focus_columns=["ProfileReviewCompletedTs"],
            root_cause_family="source_column_disappearance",
            decision="upstream_source_check_required",
            expected_keywords=["last_reviewed", "ProfileReviewCompletedTs", "upstream"],
            mapping_rows=[
                _mapping("tprofile_old", "tprofile_new", "profile_id", "ProfileIdentifier"),
                _mapping("tprofile_old", "tprofile_new", "last_reviewed", "ProfileReviewCompletedTs"),
            ],
            old_script=_old_source_script(
                ["src_profile_base", "src_profile_audit"],
                join_key="profile_id",
                id_column="profile_id",
                focus_column="last_reviewed",
            ),
            new_script=_new_source_script(
                ["src_profile_base", "src_profile_audit"],
                join_key="ProfileIdentifier",
                id_column="ProfileIdentifier",
                focus_column="ProfileReviewCompletedTs",
            ),
        ),
        _scenario(
            scenario_id="fin_tledger_wrong_business_alias",
            golden=True,
            scenario_type="alias_mismatch",
            division="FIN",
            table_name="TLEDGER",
            source_tables=["src_ledger_header", "src_ledger_status"],
            owner_users=["ledger_owner", "data_support_fin"],
            support_team="data_team_fin",
            business_description="Ledger entries and posting status.",
            criticality="high",
            issue_title="FIN_TLEDGER_Column LedgerMigrationStatus missing",
            focus_columns=["LedgerMigrationStatus"],
            root_cause_family="alias_mismatch",
            decision="regression_detected",
            expected_keywords=["legacy_flag", "LedgerMigrationStatus", "LedgerMigrationStatusText"],
            mapping_rows=[
                _mapping("tledger_old", "tledger_new", "ledger_id", "LedgerIdentifier"),
                _mapping("tledger_old", "tledger_new", "legacy_flag", "LedgerMigrationStatus"),
            ],
            old_script=_old_alias_script(
                ["src_ledger_header", "src_ledger_status"],
                join_key="ledger_id",
                id_column="ledger_id",
                focus_column="legacy_flag",
                companion_column=None,
            ),
            new_script=_new_alias_mismatch_script(
                ["src_ledger_header", "src_ledger_status"],
                join_key="LedgerIdentifier",
                id_column="LedgerIdentifier",
                source_column="LedgerStatusSourceCode",
                expected_column="LedgerMigrationStatus",
                wrong_column="LedgerMigrationStatusText",
                companion_column=None,
            ),
        ),
        _scenario(
            scenario_id="ops_tbalance_insufficient_evidence",
            golden=True,
            scenario_type="insufficient_evidence",
            division="OPS",
            table_name="TBALANCE",
            source_tables=["src_balance_header", "src_balance_snapshot"],
            owner_users=["balance_owner", "data_support_ops"],
            support_team="data_team_ops",
            business_description="Balance tracking table with periodic snapshots.",
            criticality="low",
            issue_title="OPS_TBALANCE_Column GovernanceReviewIndex mismatch",
            focus_columns=["GovernanceReviewIndex"],
            root_cause_family="insufficient_evidence",
            decision="insufficient_evidence",
            expected_keywords=["review_score", "GovernanceReviewIndex", "insufficient"],
            mapping_rows=[
                _mapping("tbalance_old", "tbalance_new", "balance_id", "BalanceIdentifier"),
                _mapping("tbalance_old", "tbalance_new", "review_score", "GovernanceReviewIndex"),
            ],
            old_script=_old_insufficient_script(
                ["src_balance_header", "src_balance_snapshot"],
                id_column="balance_id",
            ),
            new_script=_new_insufficient_script(
                ["src_balance_header", "src_balance_snapshot"],
                id_column="BalanceIdentifier",
            ),
        ),
    ]


def _generated_scenarios(seed: int) -> List[Dict]:
    rng = random.Random(seed)
    generated_specs = [
        {
            "scenario_id": "generated_payment_projection_1",
            "scenario_type": "missing_final_select",
            "division": "FIN",
            "table_name": "TPAYMENTQUALITY",
            "source_tables": ["src_payment_base", "src_payment_audit"],
            "owner_users": ["fin_owner", "data_support_fin"],
            "support_team": "data_team_fin",
            "business_description": "Generated payment quality fixture.",
            "criticality": rng.choice(["medium", "high"]),
            "issue_title": "FIN_TPAYMENTQUALITY_Column PaymentQualityIndex missing",
            "focus_columns": ["PaymentQualityIndex"],
            "root_cause_family": "missing_final_select",
            "decision": "regression_detected",
            "expected_keywords": ["payment_score", "PaymentQualityIndex"],
            "mapping_rows": [
                _mapping("tpaymentquality_old", "tpaymentquality_new", "payment_id", "PaymentIdentifier"),
                _mapping("tpaymentquality_old", "tpaymentquality_new", "payment_score", "PaymentQualityIndex"),
            ],
            "old_script": _old_projection_script(
                ["src_payment_base", "src_payment_audit"],
                join_key="payment_id",
                id_column="payment_id",
                name_column="payment_category",
                focus_column="payment_score",
                aux_column="score_updated_by",
            ),
            "new_script": _new_projection_script_missing(
                ["src_payment_base", "src_payment_audit"],
                join_key="PaymentIdentifier",
                id_column="PaymentIdentifier",
                name_column="PaymentCategoryName",
                focus_column="PaymentQualityIndex",
                aux_column="ScoreUpdatedByUser",
            ),
        },
        {
            "scenario_id": "generated_shipment_alias_2",
            "scenario_type": "alias_mismatch",
            "division": "OPS",
            "table_name": "TSHIPMENT",
            "source_tables": ["src_shipment_base", "src_shipment_status"],
            "owner_users": ["ops_owner", "data_support_ops"],
            "support_team": "data_team_ops",
            "business_description": "Generated shipment status fixture.",
            "criticality": rng.choice(["medium", "high"]),
            "issue_title": "OPS_TSHIPMENT_Column ShipmentStatus missing",
            "focus_columns": ["ShipmentStatus"],
            "root_cause_family": "alias_mismatch",
            "decision": "regression_detected",
            "expected_keywords": ["shpmnt_status", "ShipmentStatus"],
            "mapping_rows": [
                _mapping("tshipment_old", "tshipment_new", "shipment_id", "ShipmentIdentifier"),
                _mapping("tshipment_old", "tshipment_new", "shpmnt_status", "ShipmentStatus"),
            ],
            "old_script": _old_alias_script(
                ["src_shipment_base", "src_shipment_status"],
                join_key="shipment_id",
                id_column="shipment_id",
                focus_column="shpmnt_status",
                companion_column=None,
            ),
            "new_script": _new_alias_mismatch_script(
                ["src_shipment_base", "src_shipment_status"],
                join_key="ShipmentIdentifier",
                id_column="ShipmentIdentifier",
                source_column="ShipmentStatusSourceCode",
                expected_column="ShipmentStatus",
                wrong_column="ShipmentStatusLabel",
                companion_column=None,
            ),
        },
        {
            "scenario_id": "generated_invoice_derivation_3",
            "scenario_type": "renamed_derivation",
            "division": "FIN",
            "table_name": "TBILLINGVARIANCE",
            "source_tables": ["src_billing_base", "src_billing_adjustment"],
            "owner_users": ["billing_owner", "data_support_fin"],
            "support_team": "data_team_fin",
            "business_description": "Generated billing variance fixture.",
            "criticality": rng.choice(["low", "medium"]),
            "issue_title": "FIN_TBILLINGVARIANCE_Column BillingVarianceAmount missing",
            "focus_columns": ["BillingVarianceAmount"],
            "root_cause_family": "renamed_derivation",
            "decision": "regression_detected",
            "expected_keywords": ["invoice_variance", "BillingVarianceAmount"],
            "mapping_rows": [
                _mapping("tbillingvariance_old", "tbillingvariance_new", "bill_id", "BillingIdentifier"),
                _mapping("tbillingvariance_old", "tbillingvariance_new", "invoice_variance", "BillingVarianceAmount"),
            ],
            "old_script": _old_derivation_script(
                ["src_billing_base", "src_billing_adjustment"],
                join_key="bill_id",
                amount_column="invoice_amount",
                rate_column="adjustment_ratio",
                derived_column="invoice_variance",
            ),
            "new_script": _new_derivation_script_wrong(
                ["src_billing_base", "src_billing_adjustment"],
                join_key="BillingIdentifier",
                amount_column="BillingAmountValue",
                rate_column="AdjustmentRatioValue",
                expected_column="BillingVarianceAmount",
                wrong_column="BillingVarianceValue",
            ),
        },
        {
            "scenario_id": "generated_profile_source_4",
            "scenario_type": "source_column_disappearance",
            "division": "TTY",
            "table_name": "TPROFILEAUDIT",
            "source_tables": ["src_profile_stage", "src_profile_history"],
            "owner_users": ["profile_owner", "data_support_tty"],
            "support_team": "data_team_tty",
            "business_description": "Generated profile audit fixture.",
            "criticality": rng.choice(["medium", "high"]),
            "issue_title": "TTY_TPROFILEAUDIT_Column ProfileGovernanceReviewTs missing",
            "focus_columns": ["ProfileGovernanceReviewTs"],
            "root_cause_family": "source_column_disappearance",
            "decision": "upstream_source_check_required",
            "expected_keywords": ["reviewed_on", "ProfileGovernanceReviewTs"],
            "mapping_rows": [
                _mapping("tprofileaudit_old", "tprofileaudit_new", "profile_key", "ProfileIdentifier"),
                _mapping("tprofileaudit_old", "tprofileaudit_new", "reviewed_on", "ProfileGovernanceReviewTs"),
            ],
            "old_script": _old_source_script(
                ["src_profile_stage", "src_profile_history"],
                join_key="profile_key",
                id_column="profile_key",
                focus_column="reviewed_on",
            ),
            "new_script": _new_source_script(
                ["src_profile_stage", "src_profile_history"],
                join_key="ProfileIdentifier",
                id_column="ProfileIdentifier",
                focus_column="ProfileGovernanceReviewTs",
            ),
        },
    ]
    return [_scenario(golden=False, **spec) for spec in generated_specs]


def _scenario(
    scenario_id: str,
    golden: bool,
    scenario_type: str,
    division: str,
    table_name: str,
    source_tables: List[str],
    owner_users: List[str],
    support_team: str,
    business_description: str,
    criticality: str,
    issue_title: str,
    focus_columns: List[str],
    root_cause_family: str,
    decision: str,
    expected_keywords: List[str],
    mapping_rows: List[Dict],
    old_script: str,
    new_script: str,
) -> Dict:
    return {
        "id": scenario_id,
        "golden": golden,
        "scenario_type": scenario_type,
        "division": division,
        "table_name": table_name,
        "old_target_table_name": f"{table_name.lower()}_old",
        "new_target_table_name": f"{table_name.lower()}_new",
        "source_tables": source_tables,
        "owner_users": owner_users,
        "support_team": support_team,
        "business_description": business_description,
        "criticality": criticality,
        "issue_title": issue_title,
        "focus_columns": focus_columns,
        "root_cause_family": root_cause_family,
        "decision": decision,
        "expected_keywords": expected_keywords,
        "mapping_rows": mapping_rows,
        "old_script": old_script,
        "new_script": new_script,
    }


def _mapping(old_table: str, new_table: str, old_col: str, new_col: str) -> Dict:
    return {
        "old_system": "Gavin2",
        "new_system": "Gavin3",
        "old_table_name": old_table,
        "new_table_name": new_table,
        "old_column_name": old_col,
        "new_column_name": new_col,
        "data_type_old": _data_type_for(old_col),
        "data_type_new": _data_type_for(new_col),
    }


def _data_type_for(column_name: str) -> str:
    normalized = "".join(char for char in str(column_name).lower() if char.isalnum())
    timestamp_markers = (
        "updateddate",
        "dateupdated",
        "reviewcompletedts",
        "reviewedon",
        "lastreviewed",
        "effectivets",
        "governancereviewts",
    )
    if normalized.endswith(("date", "ts", "timestamp")) or any(marker in normalized for marker in timestamp_markers):
        return "timestamp"
    numeric_markers = ("amount", "value", "ratio", "tax", "score", "index", "variance")
    if any(marker in normalized for marker in numeric_markers):
        return "decimal"
    return "string"


def _old_projection_script(source_tables: List[str], join_key: str, id_column: str, name_column: str, focus_column: str, aux_column: str) -> str:
    return f"""from pyspark.sql import functions as F


def transform({source_tables[0]}, {source_tables[1]}):
    audit_snapshot = {source_tables[1]}.select(
        "{join_key}",
        "{focus_column}",
        "{aux_column}",
    )

    return (
        {source_tables[0]}.alias("base")
        .join(audit_snapshot.alias("audit"), on="{join_key}", how="left")
        .select(
            F.col("base.{id_column}").alias("{id_column}"),
            F.col("base.{name_column}").alias("{name_column}"),
            F.col("audit.{focus_column}").alias("{focus_column}"),
            F.col("audit.{aux_column}").alias("{aux_column}"),
        )
    )
"""


def _new_projection_script_missing(source_tables: List[str], join_key: str, id_column: str, name_column: str, focus_column: str, aux_column: str) -> str:
    return f"""from pyspark.sql import functions as F


def transform({source_tables[0]}, {source_tables[1]}):
    audit_snapshot = {source_tables[1]}.select(
        "{join_key}",
        "{aux_column}",
    )

    return (
        {source_tables[0]}.alias("base")
        .join(audit_snapshot.alias("audit"), on="{join_key}", how="left")
        .select(
            F.col("base.{id_column}").alias("{id_column}"),
            F.col("base.{name_column}").alias("{name_column}"),
            F.col("audit.{aux_column}").alias("{aux_column}"),
        )
    )
"""


def _old_alias_script(source_tables: List[str], join_key: str, id_column: str, focus_column: str, companion_column: str) -> str:
    companion_select = ""
    if companion_column:
        companion_select = f'\n            F.col("master.{companion_column}").alias("{companion_column}"),'
    return f"""from pyspark.sql import functions as F


def transform({source_tables[0]}, {source_tables[1]}):
    return (
        {source_tables[0]}.alias("master")
        .join({source_tables[1]}.alias("status"), on="{join_key}", how="left")
        .select(
            F.col("master.{id_column}").alias("{id_column}"),{companion_select}
            F.col("status.{focus_column}").alias("{focus_column}"),
        )
    )
"""


def _new_alias_mismatch_script(source_tables: List[str], join_key: str, id_column: str, source_column: str, expected_column: str, wrong_column: str, companion_column: str) -> str:
    companion_select = ""
    if companion_column:
        companion_select = f'\n            F.col("master.{companion_column}").alias("{companion_column}"),'
    return f"""from pyspark.sql import functions as F


def transform({source_tables[0]}, {source_tables[1]}):
    return (
        {source_tables[0]}.alias("master")
        .join({source_tables[1]}.alias("status"), on="{join_key}", how="left")
        .select(
            F.col("master.{id_column}").alias("{id_column}"),{companion_select}
            F.col("status.{source_column}").alias("{wrong_column}"),
        )
    )
"""


def _old_derivation_script(source_tables: List[str], join_key: str, amount_column: str, rate_column: str, derived_column: str) -> str:
    return f"""from pyspark.sql import functions as F


def transform({source_tables[0]}, {source_tables[1]}):
    return (
        {source_tables[0]}.alias("header")
        .join({source_tables[1]}.alias("tax"), on="{join_key}", how="left")
        .withColumn("{derived_column}", F.col("header.{amount_column}") * F.col("tax.{rate_column}"))
        .select("{join_key}", "{amount_column}", "{derived_column}")
    )
"""


def _new_derivation_script_wrong(source_tables: List[str], join_key: str, amount_column: str, rate_column: str, expected_column: str, wrong_column: str) -> str:
    return f"""from pyspark.sql import functions as F


def transform({source_tables[0]}, {source_tables[1]}):
    return (
        {source_tables[0]}.alias("header")
        .join({source_tables[1]}.alias("tax"), on="{join_key}", how="left")
        .withColumn("{wrong_column}", F.col("header.{amount_column}") * F.col("tax.{rate_column}"))
        .select("{join_key}", "{amount_column}", "{wrong_column}")
    )
"""


def _old_join_script(source_tables: List[str], join_key: str, focus_column: str) -> str:
    return f"""from pyspark.sql import functions as F


def transform({source_tables[0]}, {source_tables[1]}):
    return (
        {source_tables[0]}.alias("header")
        .join({source_tables[1]}.alias("status"), on="{join_key}", how="left")
        .select("{join_key}", F.col("status.{focus_column}").alias("{focus_column}"))
    )
"""


def _new_join_script(source_tables: List[str], join_keys: List[str], focus_column: str, filter_column: str) -> str:
    join_literal = "[" + ", ".join(f'"{key}"' for key in join_keys) + "]"
    return f"""from pyspark.sql import functions as F


def transform({source_tables[0]}, {source_tables[1]}):
    status_filtered = {source_tables[1]}.filter(F.col("{filter_column}").isNotNull())
    return (
        {source_tables[0]}.alias("header")
        .join(status_filtered.alias("status"), on={join_literal}, how="left")
        .select("{join_keys[0]}", F.col("status.{focus_column}").alias("{focus_column}"))
    )
"""


def _old_filter_script(source_tables: List[str], join_key: str, id_column: str, focus_column: str) -> str:
    return f"""from pyspark.sql import functions as F


def transform({source_tables[0]}, {source_tables[1]}):
    return (
        {source_tables[0]}.alias("inventory")
        .join({source_tables[1]}.alias("warehouse"), on="{join_key}", how="left")
        .select("{id_column}", F.col("warehouse.{focus_column}").alias("{focus_column}"))
    )
"""


def _new_filter_script(source_tables: List[str], join_key: str, id_column: str, focus_column: str) -> str:
    return f"""from pyspark.sql import functions as F


def transform({source_tables[0]}, {source_tables[1]}):
    return (
        {source_tables[0]}.alias("inventory")
        .join({source_tables[1]}.alias("warehouse"), on="{join_key}", how="left")
        .filter(F.col("warehouse.{focus_column}") == "ACTIVE")
        .select("{id_column}", F.col("warehouse.{focus_column}").alias("{focus_column}"))
    )
"""


def _old_source_script(source_tables: List[str], join_key: str, id_column: str, focus_column: str) -> str:
    return f"""from pyspark.sql import functions as F


def transform({source_tables[0]}, {source_tables[1]}):
    audit_cols = {source_tables[1]}.select("{join_key}", "{focus_column}")
    return (
        {source_tables[0]}.alias("base")
        .join(audit_cols.alias("audit"), on="{join_key}", how="left")
        .select("{id_column}", F.col("audit.{focus_column}").alias("{focus_column}"))
    )
"""


def _new_source_script(source_tables: List[str], join_key: str, id_column: str, focus_column: str) -> str:
    return f"""from pyspark.sql import functions as F


def transform({source_tables[0]}, {source_tables[1]}):
    audit_cols = {source_tables[1]}.select("{join_key}")
    return (
        {source_tables[0]}.alias("base")
        .join(audit_cols.alias("audit"), on="{join_key}", how="left")
        .select("{id_column}")
    )
"""


def _old_insufficient_script(source_tables: List[str], id_column: str) -> str:
    return f"""from pyspark.sql import functions as F


def transform({source_tables[0]}, {source_tables[1]}):
    return {source_tables[0]}.select("{id_column}", "balance_amount")
"""


def _new_insufficient_script(source_tables: List[str], id_column: str) -> str:
    return f"""from pyspark.sql import functions as F


def transform({source_tables[0]}, {source_tables[1]}):
    return {source_tables[1]}.select("{id_column}", "balance_amount_snapshot")
"""

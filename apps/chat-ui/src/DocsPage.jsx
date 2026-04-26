import { Link } from "react-router-dom";

const bugArchitectureHighlights = [
    {
        title: "System 1",
        description: "Parses the Jira title, extracts division, table, and issue details, and classifies whether the incident is infra-related or data-related.",
    },
    {
        title: "System 2",
        description: "Resolves ownership, source tables, target tables, and old-to-new column mapping from the workbook fixtures.",
    },
    {
        title: "System 3",
        description: "Analyzes the old and new scripts independently, compares the behaviors, and produces a focused human-readable investigation summary.",
    },
    {
        title: "System 4",
        description: "Queries SQLite target-table fixtures, runs deterministic SQL diagnostics, and grounds the final explanation against the new-script analysis.",
    },
    {
        title: "Orchestrator",
        description: "Runs the end-to-end flow for the UI and returns the structured response that powers the investigation dashboard.",
    },
];

const bugFlowSteps = [
    "The user submits a Jira title from the UI.",
    "The orchestrator calls System 1 to parse the title, extract the issue, and classify the routing path.",
    "If the issue is data-related, System 2 resolves target-table metadata and old-to-new column mappings.",
    "System 3 analyzes the old script and new script independently using the resolved mapping context.",
    "System 4 queries SQLite target-table fixtures, runs deterministic diagnostics, and compares those findings with the new-script analysis.",
    "The orchestrator returns a structured response with root cause, SQL evidence, and next-step guidance for the analyst.",
];

const system4Highlights = [
    {
        title: "SQLite Evidence Layer",
        details: "System 4 uses seeded current-target-table and support-table fixtures so every SQL finding is grounded in reproducible mock data.",
    },
    {
        title: "Deterministic Checks",
        details: "It runs issue-focused SQL diagnostics such as missing-column checks, duplicate detection, and basic data-shape validation before any optional LLM explanation.",
    },
    {
        title: "Script Comparison",
        details: "The SQL symptoms are compared with the new-script analysis so the output connects target-table behavior back to transformation logic.",
    },
    {
        title: "Analyst Output",
        details: "The UI surfaces current target-table query results, diagnostic SQL findings, and a grounded SQL-versus-script explanation with code references.",
    },
];

const bugDataSources = [
    {
        title: "Column Mapping Workbook",
        details: "Gavin2-to-Gavin3 renamed-column mappings for each target table, including old and new data types.",
    },
    {
        title: "Table Metadata Workbook",
        details: "Division ownership, source tables, old and new target tables, support team, owners, and script paths.",
    },
    {
        title: "Old and New PySpark Scripts",
        details: "Repo-local script fixtures used to compare legacy logic against the new Gavin3 transformation flow.",
    },
    {
        title: "SQLite Target Table Fixtures",
        details: "Seeded target-table and support-table rows used directly by System 4 for issue-focused SQL diagnostics and grounded comparison.",
    },
    {
        title: "Scenario Catalog",
        details: "Curated bug scenarios that keep the mock data aligned to realistic migration regressions.",
    },
];

const sampleMappingRows = [
    {
        old_system: "Gavin2",
        new_system: "Gavin3",
        old_table_name: "tentity_old",
        new_table_name: "tentity_new",
        old_column_name: "entity_id",
        new_column_name: "EntityIdentifier",
        data_type_old: "string",
        data_type_new: "string",
    },
    {
        old_system: "Gavin2",
        new_system: "Gavin3",
        old_table_name: "tentity_old",
        new_table_name: "tentity_new",
        old_column_name: "entity_name",
        new_column_name: "EntityDisplayName",
        data_type_old: "string",
        data_type_new: "string",
    },
    {
        old_system: "Gavin2",
        new_system: "Gavin3",
        old_table_name: "tentity_old",
        new_table_name: "tentity_new",
        old_column_name: "date_updated",
        new_column_name: "UPDATEDDATE",
        data_type_old: "timestamp",
        data_type_new: "timestamp",
    },
    {
        old_system: "Gavin2",
        new_system: "Gavin3",
        old_table_name: "tentity_old",
        new_table_name: "tentity_new",
        old_column_name: "updated_by",
        new_column_name: "UpdatedByUser",
        data_type_old: "string",
        data_type_new: "string",
    },
];

const sampleOldScript = `from pyspark.sql import functions as F


def transform(src_tentity_base, src_tentity_audit):
    audit_snapshot = src_tentity_audit.select(
        "entity_id",
        "date_updated",
        "updated_by",
    )

    return (
        src_tentity_base.alias("base")
        .join(audit_snapshot.alias("audit"), on="entity_id", how="left")
        .select(
            F.col("base.entity_id").alias("entity_id"),
            F.col("base.entity_name").alias("entity_name"),
            F.col("audit.date_updated").alias("date_updated"),
            F.col("audit.updated_by").alias("updated_by"),
        )
    )`;

const sampleNewScript = `from pyspark.sql import functions as F


def transform(src_tentity_base, src_tentity_audit):
    audit_snapshot = src_tentity_audit.select(
        "EntityIdentifier",
        "UpdatedByUser",
    )

    return (
        src_tentity_base.alias("base")
        .join(audit_snapshot.alias("audit"), on="EntityIdentifier", how="left")
        .select(
            F.col("base.EntityIdentifier").alias("EntityIdentifier"),
            F.col("base.EntityDisplayName").alias("EntityDisplayName"),
            F.col("audit.UpdatedByUser").alias("UpdatedByUser"),
        )
    )`;

const analystOutputs = [
    "Issue summary and routing decision from the orchestrator.",
    "Old target table and new target table context from System 2.",
    "Issue-focused column mapping plus full target-table mapping coverage.",
    "Old script analysis and new script analysis from System 3.",
    "Current target-table SQL query results and deterministic diagnostic SQL checks from System 4.",
    "A grounded SQL-versus-new-script explanation with affected code references.",
    "Likely root cause, possible resolutions, and recommended next step.",
    "Evidence snippets and script references when expanded.",
];

const bugAiUsageCards = [
    {
        title: "Where AI Is Used",
        details: "System 1 is rules-first and only uses AI as a fallback for low-confidence parsing or classification. System 2 stays fully deterministic, and System 3 remains the main AI analysis layer.",
    },
    {
        title: "How AI Is Used",
        details: "For a normal data issue, System 3 runs old-script analysis, new-script analysis, and synthesis. System 4 can add one extra grounded comparison call after deterministic SQL diagnostics to explain the target-table symptoms against the new script.",
    },
    {
        title: "Current Model",
        details: "The shared OpenAI client is currently configured to use gpt-4o-mini by default unless OPENAI_CHAT_MODEL is overridden in the environment.",
    },
    {
        title: "Why This Model",
        details: "It keeps the POC fast and inexpensive while still being strong enough for structured JSON analysis and grounded comparison of script and SQL evidence.",
    },
];

const bugAiCostNotes = [
    "System 1 normally stays rule-based, but a low-confidence title can trigger one extra fallback LLM call for parsing and classification.",
    "A typical data investigation triggers three LLM calls in System 3: old-script analysis, new-script analysis, and synthesis.",
    "System 4 can add one more grounded LLM call after deterministic SQL diagnostics to explain how current target-table data lines up with the new script.",
    "Using the current default model gpt-4o-mini, a small POC investigation usually lands in the low-thousand-token range and is typically a fraction of a cent to a few tenths of a cent per issue.",
    "A reasonable working estimate for this POC is about $0.003 to $0.007 per normal data issue, with slightly higher cost when System 1 also needs the AI fallback.",
    "Infra issues short-circuit after System 1, so they do not need the full LLM path in Systems 3 and 4.",
    "Costs can increase if we send larger script excerpts, longer evidence blocks, or switch to a more capable model.",
];

const monitoringOverviewCards = [
    {
        title: "Primary Use Case",
        details: "Monitor scheduled Azure Data Factory or Azure Synapse pipelines in one operational view instead of waiting for issue-by-issue investigation.",
    },
    {
        title: "Operational Focus",
        details: "The dashboard prioritizes historical health, recent failures, retries, and duration regressions rather than second-by-second live status.",
    },
    {
        title: "Current Data Mode",
        details: "The POC currently runs on seeded observability fixtures that resemble Log Analytics output so the UI and API remain deterministic during development.",
    },
    {
        title: "Where To Use It",
        details: "The interactive experience lives on the live monitoring dashboard at /#/observability, while this section explains the architecture and behavior behind it.",
    },
];

const monitoringArchitectureSteps = [
    "Azure Data Factory or Azure Synapse emits diagnostic events for pipeline, activity, and trigger runs.",
    "Those diagnostics flow into a Log Analytics workspace that becomes the primary historical telemetry source.",
    "The FastAPI backend queries and normalizes the run data, then joins it with app-owned metadata such as cadence, owner, and criticality.",
    "The observability API returns summary metrics, grouped pipeline health, drilldown detail, AI summary context, and natural-language query results.",
    "The React dashboard renders filters, pipeline cards, grouped health views, run history, and AI-assisted monitoring panels.",
];

const monitoringCapabilities = [
    {
        title: "Dashboard Filters",
        details: "Time window, cadence, status, owner, criticality, and pipeline search help narrow the operational scope quickly.",
    },
    {
        title: "Pipelines",
        details: "The dashboard surfaces the pipelines that need eyes first, including failures, retries, and regression signals.",
    },
    {
        title: "Grouped Health Views",
        details: "Pipelines are grouped by cadence so operators can compare daily, weekly, and monthly health from the same screen.",
    },
    {
        title: "Pipeline Drilldown",
        details: "Each pipeline has run history, retry summary, activity-level trends, failure details, and recent execution context.",
    },
    {
        title: "AI Assistance",
        details: "Operators can generate an AI summary of the current dashboard state or ask a natural-language question grounded in backend-provided data.",
    },
];

const monitoringApiSurface = [
    {
        endpoint: "GET /observability/summary",
        details: "Returns summary metrics and the pipeline card band used for the top-level monitoring view.",
    },
    {
        endpoint: "GET /observability/pipelines",
        details: "Returns grouped pipeline health and list data filtered by cadence, status, owner, criticality, and search.",
    },
    {
        endpoint: "GET /observability/pipelines/{pipeline_name}",
        details: "Returns run history, retry patterns, activity summaries, and detailed failure context for a selected pipeline.",
    },
    {
        endpoint: "POST /observability/summary-ai",
        details: "Builds a grounded AI summary from the current summary metrics and grouped pipeline data already loaded by the UI.",
    },
    {
        endpoint: "POST /observability/query",
        details: "Translates a natural-language question into a safe observability query plan and summarized response grounded in backend results.",
    },
];

const monitoringDataSources = [
    {
        title: "ADFPipelineRun",
        details: "Primary pipeline-level run history for summary metrics, latest status, duration tracking, and trend analysis.",
    },
    {
        title: "ADFActivityRun",
        details: "Activity-level telemetry used for detailed failure context, retry analysis, and downstream drilldown insights.",
    },
    {
        title: "ADFTriggerRun",
        details: "Trigger execution context used to explain cadence behavior, missed schedules, and trigger-linked run patterns.",
    },
    {
        title: "App-Owned Metadata",
        details: "Cadence, owner, criticality, and related business metadata are maintained by the application instead of being inferred only from logs.",
    },
    {
        title: "Seeded Mock Fixtures",
        details: "The current POC uses fixture bundles under the observability fixture root so the same backend processing path can later point at a real Log Analytics workspace.",
    },
];

const monitoringAiCards = [
    {
        title: "Summary Generation",
        details: "The AI summary endpoint explains the current dashboard state by grounding every statement in the summary metrics and grouped pipeline rows already fetched by the backend.",
    },
    {
        title: "Natural-Language Querying",
        details: "The query assistant converts plain-English operational questions into a safe query plan and response shape instead of letting the browser hit telemetry sources directly.",
    },
    {
        title: "Guardrails",
        details: "All Azure credentials, workspace access, and query execution remain server-side, so AI assistance works only on backend-provided observability data.",
    },
];

const azureGuideOverviewCards = [
    {
        title: "Private-Only Landing Zone",
        details: "Keep the app tier, observability path, and data integrations in the same subscription as the existing ADLS Gen2 account while exposing access only through private network paths such as VPN or ExpressRoute.",
    },
    {
        title: "Unified Backend Role",
        details: "Deploy the React UI and the unified FastAPI backend as separate private app components, with the backend remaining the only layer that talks to Azure data services, Log Analytics, and model endpoints.",
    },
    {
        title: "ADLS2 Access Pattern",
        details: "Treat ADLS Gen2 as the source of truth for table metadata and business tables, but read it through a governed SQL or query layer instead of direct browser or raw storage access.",
    },
    {
        title: "Observability Flow",
        details: "Send Azure Data Factory or Synapse pipeline diagnostics into Log Analytics, then let the backend normalize that telemetry and join it with cadence, owner, and criticality metadata.",
    },
    {
        title: "Security Model",
        details: "Disable public network access where supported, use private endpoints plus private DNS, and grant managed identities only the reader, pull, and secret-access roles they need.",
    },
];

const azureResourceInventoryRows = [
    {
        resource_group: "rg-bugmgmt-net-prod",
        resource: "Virtual network",
        proposed_name: "vnet-bugmgmt-prod",
        purpose: "Private application network that hosts the app gateway, Container Apps environment, private endpoints, and supporting DNS subnets.",
    },
    {
        resource_group: "rg-bugmgmt-net-prod",
        resource: "Application Gateway WAF v2",
        proposed_name: "agw-bugmgmt-prod",
        purpose: "Private-only frontend entry point that publishes the docs and app UI without opening a public endpoint.",
    },
    {
        resource_group: "rg-bugmgmt-app-prod",
        resource: "Container Apps environment",
        proposed_name: "acae-bugmgmt-prod",
        purpose: "Internal-only environment for the private UI and API workloads.",
    },
    {
        resource_group: "rg-bugmgmt-app-prod",
        resource: "Container App - UI",
        proposed_name: "ca-bugmgmt-ui-prod",
        purpose: "Hosts the React docs and monitoring interface as the private web tier.",
    },
    {
        resource_group: "rg-bugmgmt-app-prod",
        resource: "Container App - API",
        proposed_name: "ca-bugmgmt-api-prod",
        purpose: "Runs the unified FastAPI backend that serves investigation and observability endpoints.",
    },
    {
        resource_group: "rg-bugmgmt-platform-prod",
        resource: "Azure Container Registry Premium",
        proposed_name: "acrbugmgmtprod",
        purpose: "Private image registry used by the Container Apps workloads.",
    },
    {
        resource_group: "rg-bugmgmt-platform-prod",
        resource: "Key Vault",
        proposed_name: "kv-bugmgmt-prod",
        purpose: "Stores application secrets, certificates, and future shared configuration values.",
    },
    {
        resource_group: "rg-bugmgmt-platform-prod",
        resource: "Azure OpenAI",
        proposed_name: "aoai-bugmgmt-prod",
        purpose: "Private model endpoint for the structured AI calls already used by the investigation and observability layers.",
    },
    {
        resource_group: "rg-bugmgmt-data-prod",
        resource: "Existing ADLS Gen2 account",
        proposed_name: "keep current",
        purpose: "Remains the source of truth for metadata tables and business data inside the same subscription.",
    },
    {
        resource_group: "rg-bugmgmt-data-prod",
        resource: "Synapse workspace",
        proposed_name: "syn-bugmgmt-prod",
        purpose: "Provides the governed query layer that reads ADLS2 data for metadata and SQL-style diagnostics.",
    },
    {
        resource_group: "rg-bugmgmt-data-prod",
        resource: "Data Factory",
        proposed_name: "adf-bugmgmt-prod",
        purpose: "Owns scheduled pipeline execution and emits telemetry into the monitoring path.",
    },
    {
        resource_group: "rg-bugmgmt-ops-prod",
        resource: "Log Analytics workspace",
        proposed_name: "law-bugmgmt-prod",
        purpose: "Central workspace for ADF, Synapse, app, and platform diagnostics queried by the observability backend.",
    },
    {
        resource_group: "rg-bugmgmt-ops-prod",
        resource: "Application Insights",
        proposed_name: "appi-bugmgmt-prod",
        purpose: "Workspace-based app telemetry for the private UI and API workloads.",
    },
    {
        resource_group: "rg-bugmgmt-ops-prod",
        resource: "Azure Monitor Private Link Scope",
        proposed_name: "ampls-bugmgmt-prod",
        purpose: "Keeps Azure Monitor and Log Analytics query traffic on private network paths.",
    },
];

const azureNetworkLayoutRows = [
    {
        subnet: "snet-appgw",
        cidr: "10.42.0.0/24",
        purpose: "Dedicated subnet for the private Application Gateway WAF deployment.",
        notes: "Reserve this subnet for the gateway only.",
    },
    {
        subnet: "snet-aca-env",
        cidr: "10.42.1.0/24",
        purpose: "Dedicated subnet for the internal Azure Container Apps environment.",
        notes: "Use this for the private UI and API app tier.",
    },
    {
        subnet: "snet-private-endpoints",
        cidr: "10.42.2.0/24",
        purpose: "Consolidated subnet for private endpoint NICs.",
        notes: "Keeps data-plane private links isolated from the app tier.",
    },
    {
        subnet: "AzureBastionSubnet",
        cidr: "10.42.3.0/26",
        purpose: "Optional admin subnet for Bastion-based access.",
        notes: "Include only if private VM administration is needed.",
    },
    {
        subnet: "GatewaySubnet",
        cidr: "10.42.3.64/27",
        purpose: "Reserved subnet for VPN or ExpressRoute gateway connectivity.",
        notes: "Protects room for enterprise private access later.",
    },
    {
        subnet: "snet-dns-inbound",
        cidr: "10.42.3.96/28",
        purpose: "Inbound Azure DNS Private Resolver endpoint.",
        notes: "Lets on-prem or hub DNS reach the private Azure zones.",
    },
    {
        subnet: "snet-dns-outbound",
        cidr: "10.42.3.112/28",
        purpose: "Outbound Azure DNS Private Resolver endpoint.",
        notes: "Supports forwarding private name resolution to enterprise DNS when required.",
    },
];

const azurePrivateAccessRows = [
    {
        target: "ADLS Gen2",
        private_endpoints: "pe-adls-blob-prod, pe-adls-dfs-prod",
        dns_zones: "privatelink.blob.core.windows.net, privatelink.dfs.core.windows.net",
        notes: "Both blob and dfs endpoints are needed for the storage account.",
    },
    {
        target: "Key Vault",
        private_endpoints: "pe-kv-prod",
        dns_zones: "privatelink.vaultcore.azure.net",
        notes: "Keep public network access disabled.",
    },
    {
        target: "Azure Container Registry",
        private_endpoints: "pe-acr-prod",
        dns_zones: "privatelink.azurecr.io",
        notes: "Premium SKU is required for Private Link.",
    },
    {
        target: "Azure OpenAI",
        private_endpoints: "pe-aoai-prod",
        dns_zones: "privatelink.openai.azure.com",
        notes: "Use Entra auth and keep model access server-side.",
    },
    {
        target: "Synapse workspace",
        private_endpoints: "pe-syn-sql-prod, pe-syn-sqlod-prod, pe-syn-dev-prod",
        dns_zones: "privatelink.sql.azuresynapse.net, privatelink.dev.azuresynapse.net",
        notes: "Add the workspace web endpoint if Studio access is required.",
    },
    {
        target: "Azure Monitor and Log Analytics",
        private_endpoints: "pe-ampls-prod",
        dns_zones: "privatelink.monitor.azure.com, privatelink.oms.opinsights.azure.com, privatelink.ods.opinsights.azure.com, privatelink.agentsvc.azure-automation.net",
        notes: "Route monitoring queries and ingestion through AMPLS for private access.",
    },
    {
        target: "ADF control plane",
        private_endpoints: "pe-adf-api-prod, pe-adf-portal-prod",
        dns_zones: "privatelink.datafactory.azure.net, privatelink.adf.azure.com",
        notes: "Add if private control-plane access is required for the factory experience.",
    },
];

const azureAccessModelRows = [
    {
        principal: "grp-bugmgmt-platform-admins",
        scope: "App, data, network, and ops resource groups",
        roles: "Contributor",
        notes: "Primary engineering ownership group for the landing zone.",
    },
    {
        principal: "grp-bugmgmt-security-admins",
        scope: "Same production scopes",
        roles: "User Access Administrator",
        notes: "Limit this to a very small admin set.",
    },
    {
        principal: "grp-bugmgmt-network-ops",
        scope: "rg-bugmgmt-net-prod",
        roles: "Network Contributor, Private DNS Zone Contributor",
        notes: "Owns private networking, DNS, and gateway changes.",
    },
    {
        principal: "grp-bugmgmt-data-admins",
        scope: "ADLS Gen2 account",
        roles: "Storage Blob Data Owner",
        notes: "Owns path ACLs and storage data governance.",
    },
    {
        principal: "uami-bugmgmt-api-prod",
        scope: "ACR, Key Vault, Log Analytics, Azure OpenAI",
        roles: "AcrPull, Key Vault Secrets User, Log Analytics Data Reader, Cognitive Services OpenAI User",
        notes: "Managed identity used by the unified FastAPI backend.",
    },
    {
        principal: "uami-bugmgmt-agw-prod",
        scope: "Key Vault",
        roles: "Key Vault Secrets User",
        notes: "Lets the private gateway read TLS material from Key Vault.",
    },
    {
        principal: "Synapse workspace managed identity",
        scope: "ADLS Gen2 paths used for metadata and business tables",
        roles: "Storage Blob Data Reader plus path ACLs",
        notes: "Use this identity for governed read access into lake data.",
    },
    {
        principal: "Data Factory managed identity",
        scope: "ADLS Gen2 paths touched by pipeline execution",
        roles: "Storage Blob Data Reader or Storage Blob Data Contributor",
        notes: "Grant write only where a pipeline actually produces data.",
    },
    {
        principal: "grp-bugmgmt-observability-readers",
        scope: "Log Analytics workspace",
        roles: "Log Analytics Reader",
        notes: "Optional human read-only access for support and operations teams.",
    },
];

const azureImplementationNotes = [
    {
        title: "Proposed Defaults",
        details: "The resource names, CIDR ranges, and subnet splits below are recommended POC defaults. They should be aligned to the enterprise naming standard and IPAM plan before production rollout.",
    },
    {
        title: "ADLS2 Query Layer",
        details: "The app tier should not read lake paths directly from the browser. The preferred production pattern is backend access through Synapse serverless SQL or another governed query layer over ADLS2.",
    },
    {
        title: "Backend Entry Point",
        details: "The current repo is best suited to deploy the unified backend entry point rather than four separately exposed services, so the private app surface stays smaller and easier to secure.",
    },
    {
        title: "Monitoring Alignment",
        details: "ADF or Synapse diagnostics, application logs, and future gateway telemetry should land in the same Log Analytics workspace so the observability API can join platform signals with app-owned metadata.",
    },
    {
        title: "Container Apps Caveat",
        details: "Internal Azure Container Apps works well for the POC, but if the enterprise policy forbids any managed public egress artifacts, the app tier should be re-evaluated against ASE v3 or private AKS.",
    },
];

function DocsAccordion({ badge, copy, defaultOpen = false, title, children }) {
    return (
        <details className="panel docs-accordion" open={defaultOpen}>
            <summary>
                <div className="docs-accordion-title">
                    <h2>{title}</h2>
                    <span className="metric-badge">{badge}</span>
                </div>
                <p className="docs-accordion-copy">{copy}</p>
            </summary>
            <div className="docs-section-stack">{children}</div>
        </details>
    );
}

export default function DocsPage() {
    return (
        <section className="docs-stack">
            <section className="hero-card">
                <div className="hero-actions">
                    <div>
                        <p className="eyebrow">Project Docs</p>
                        <h1>Bug Management and Monitoring POC documentation</h1>
                        <p className="hero-copy">
                            This page covers both sides of the POC: the four-stage Jira bug investigation flow,
                            including System 4 SQL diagnostics, and the Azure pipeline monitoring experience powered
                            by the live observability dashboard.
                        </p>
                    </div>
                    <Link to="/" className="ghost nav-button">
                        Back To Investigation
                    </Link>
                    <Link to="/observability" className="ghost nav-button">
                        Open Live Monitoring
                    </Link>
                </div>
            </section>

            <section className="docs-accordion-stack">
                <DocsAccordion
                    defaultOpen
                    title="Bug Management"
                    badge="Four-stage investigation"
                    copy="Jira title parsing, script analysis, and System 4 SQL diagnostics for grounded migration investigations."
                >
                    <article className="docs-panel">
                        <p className="section-kicker">Architecture</p>
                        <h3>Service Responsibilities</h3>
                        <figure className="docs-figure">
                            <img src="/docs-images/architecture-diagram.png" alt="Architecture diagram for the bug investigation platform" />
                            <figcaption>
                                High-level architecture showing the React UI, orchestrator, four investigation stages,
                                workbook inputs, SQLite fixtures, script fixtures, and the grounded analysis flow.
                            </figcaption>
                        </figure>
                        <div className="docs-card-grid">
                            {bugArchitectureHighlights.map((item) => (
                                <div key={item.title} className="docs-info-card">
                                    <h4>{item.title}</h4>
                                    <p>{item.description}</p>
                                </div>
                            ))}
                        </div>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">Data Flow</p>
                        <h3>How a request moves through the system</h3>
                        <figure className="docs-figure">
                            <img src="/docs-images/data-flow-diagram.png" alt="Data flow diagram for Jira title investigation" />
                            <figcaption>
                                End-to-end flow from Jira title input through parsing, metadata resolution, old and
                                new script analysis, System 4 SQL diagnostics, and final structured output.
                            </figcaption>
                        </figure>
                        <ol className="docs-flow-list">
                            {bugFlowSteps.map((item) => (
                                <li key={item}>{item}</li>
                            ))}
                        </ol>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">System 4</p>
                        <h3>SQL diagnostics and grounded comparison</h3>
                        <div className="docs-card-grid">
                            {system4Highlights.map((item) => (
                                <div key={item.title} className="docs-info-card">
                                    <h4>{item.title}</h4>
                                    <p>{item.details}</p>
                                </div>
                            ))}
                        </div>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">Data Sources</p>
                        <h3>Mock data used by the POC</h3>
                        <div className="docs-card-grid">
                            {bugDataSources.map((item) => (
                                <div key={item.title} className="docs-info-card">
                                    <h4>{item.title}</h4>
                                    <p>{item.details}</p>
                                </div>
                            ))}
                        </div>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">Sample Data</p>
                        <h3>Example workbook rows and script inputs</h3>
                        <p className="hero-copy docs-copy">
                            This sample is taken from the <code>tentity_old</code> to <code>tentity_new</code>
                            migration path. It shows the renamed-column mapping and old/new PySpark logic that
                            Systems 2 and 3 resolve before System 4 checks the resulting target-table behavior.
                        </p>

                        <section className="subsection">
                            <h4>Sample Column Mapping Sheet Rows</h4>
                            <div className="table-wrap docs-table-wrap">
                                <table className="mapping-table">
                                    <thead>
                                        <tr>
                                            <th>Old System</th>
                                            <th>New System</th>
                                            <th>Old Table</th>
                                            <th>New Table</th>
                                            <th>Old Column</th>
                                            <th>New Column</th>
                                            <th>Old Type</th>
                                            <th>New Type</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {sampleMappingRows.map((row) => (
                                            <tr key={`${row.old_column_name}-${row.new_column_name}`}>
                                                <td>{row.old_system}</td>
                                                <td>{row.new_system}</td>
                                                <td>{row.old_table_name}</td>
                                                <td>{row.new_table_name}</td>
                                                <td>{row.old_column_name}</td>
                                                <td>{row.new_column_name}</td>
                                                <td>{row.data_type_old}</td>
                                                <td>{row.data_type_new}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </section>

                        <section className="docs-script-grid">
                            <div className="docs-script-card">
                                <div className="docs-script-header">
                                    <div>
                                        <p className="section-kicker">Legacy Script</p>
                                        <h4>Old PySpark Example</h4>
                                    </div>
                                    <span className="metric-badge">tentity_old flow</span>
                                </div>
                                <pre className="code-block">{sampleOldScript}</pre>
                            </div>

                            <div className="docs-script-card">
                                <div className="docs-script-header">
                                    <div>
                                        <p className="section-kicker">Target Script</p>
                                        <h4>New PySpark Example</h4>
                                    </div>
                                    <span className="metric-badge">tentity_new flow</span>
                                </div>
                                <pre className="code-block">{sampleNewScript}</pre>
                            </div>
                        </section>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">Output</p>
                        <h3>What the analyst sees in the UI</h3>
                        <ul className="detail-list">
                            {analystOutputs.map((item) => (
                                <li key={item}>{item}</li>
                            ))}
                        </ul>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">AI Layer</p>
                        <h3>How AI is used in this POC</h3>
                        <div className="docs-card-grid">
                            {bugAiUsageCards.map((item) => (
                                <div key={item.title} className="docs-info-card">
                                    <h4>{item.title}</h4>
                                    <p>{item.details}</p>
                                </div>
                            ))}
                        </div>
                        <div className="docs-card-grid">
                            <div className="docs-info-card">
                                <h4>Estimated Cost</h4>
                                <ul className="detail-list">
                                    {bugAiCostNotes.map((item) => (
                                        <li key={item}>{item}</li>
                                    ))}
                                </ul>
                            </div>
                            <div className="docs-info-card">
                                <h4>Pricing Reference</h4>
                                <p>
                                    Current pricing should be checked against the official OpenAI pricing page before
                                    using the estimate operationally.
                                </p>
                                <p>
                                    OpenAI pricing:{" "}
                                    <a
                                        className="docs-link"
                                        href="https://platform.openai.com/docs/pricing"
                                        target="_blank"
                                        rel="noreferrer"
                                    >
                                        platform.openai.com/docs/pricing
                                    </a>
                                </p>
                                <p>
                                    The default model value comes from the shared client in the repo and is currently set to
                                    <code> gpt-4o-mini </code>.
                                </p>
                            </div>
                        </div>
                    </article>
                </DocsAccordion>

                <DocsAccordion
                    title="Monitoring"
                    badge="Live dashboard docs"
                    copy="Azure pipeline health, grouped monitoring, backend-served observability APIs, and AI-assisted operational analysis."
                >
                    <article className="docs-panel">
                        <p className="section-kicker">Overview</p>
                        <h3>Monitoring POC overview</h3>
                        <p className="hero-copy docs-copy">
                            The monitoring side of the POC acts as an operational dashboard for Azure Data Factory and
                            Azure Synapse pipeline health. It complements the issue-driven investigation flow by
                            helping operators identify failing, retrying, or slowing pipelines before they escalate into
                            individual bug investigations.
                        </p>
                        <div className="docs-card-grid">
                            {monitoringOverviewCards.map((item) => (
                                <div key={item.title} className="docs-info-card">
                                    <h4>{item.title}</h4>
                                    <p>{item.details}</p>
                                </div>
                            ))}
                            <div className="docs-info-card">
                                <h4>Live Route</h4>
                                <p>
                                    Use the{" "}
                                    <Link className="docs-link" to="/observability">
                                        live monitoring dashboard
                                    </Link>{" "}
                                    for the interactive experience described in this section.
                                </p>
                            </div>
                        </div>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">Architecture</p>
                        <h3>Monitoring architecture and data path</h3>
                        <figure className="docs-figure">
                            <img
                                src="/docs-images/monitoring-architecture-diagram.png"
                                alt="Architecture diagram for the Azure pipeline monitoring POC"
                            />
                            <figcaption>
                                Monitoring architecture showing the Azure telemetry path, seeded observability fixtures,
                                metadata enrichment, backend observability service, API surface, React dashboard, and
                                AI-assisted summary/query flows.
                            </figcaption>
                        </figure>
                        <ol className="docs-flow-list">
                            {monitoringArchitectureSteps.map((item) => (
                                <li key={item}>{item}</li>
                            ))}
                        </ol>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">Capabilities</p>
                        <h3>Dashboard capabilities</h3>
                        <div className="docs-card-grid">
                            {monitoringCapabilities.map((item) => (
                                <div key={item.title} className="docs-info-card">
                                    <h4>{item.title}</h4>
                                    <p>{item.details}</p>
                                </div>
                            ))}
                        </div>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">API Surface</p>
                        <h3>Backend API surface</h3>
                        <div className="docs-card-grid">
                            {monitoringApiSurface.map((item) => (
                                <div key={item.endpoint} className="docs-info-card">
                                    <h4>
                                        <code>{item.endpoint}</code>
                                    </h4>
                                    <p>{item.details}</p>
                                </div>
                            ))}
                        </div>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">Data</p>
                        <h3>Data sources and seed strategy</h3>
                        <figure className="docs-figure">
                            <img
                                src="/docs-images/monitoring-mock-data-snapshot.png"
                                alt="Mock data snapshot for the monitoring observability fixtures"
                            />
                            <figcaption>
                                Mock observability data snapshot showing how pipeline metadata, pipeline runs,
                                activity runs, and trigger runs roll up into the dashboard interpretation layer.
                            </figcaption>
                        </figure>
                        <div className="docs-card-grid">
                            {monitoringDataSources.map((item) => (
                                <div key={item.title} className="docs-info-card">
                                    <h4>{item.title}</h4>
                                    <p>{item.details}</p>
                                </div>
                            ))}
                        </div>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">AI Layer</p>
                        <h3>AI assistance in monitoring</h3>
                        <div className="docs-card-grid">
                            {monitoringAiCards.map((item) => (
                                <div key={item.title} className="docs-info-card">
                                    <h4>{item.title}</h4>
                                    <p>{item.details}</p>
                                </div>
                            ))}
                        </div>
                    </article>
                </DocsAccordion>

                <DocsAccordion
                    title="Azure Guide"
                    badge="Private deployment blueprint"
                    copy="Concrete Azure resource, networking, private endpoint, and RBAC guidance for deploying this POC privately in the same subscription as ADLS Gen2."
                >
                    <article className="docs-panel">
                        <p className="section-kicker">Overview</p>
                        <h3>Private Azure landing zone for this POC</h3>
                        <p className="hero-copy docs-copy">
                            This guide turns the monitoring architecture into a concrete Azure deployment blueprint.
                            It assumes the application, observability services, and existing ADLS Gen2 data live in the
                            same subscription and must stay private rather than internet-facing.
                        </p>
                        <figure className="docs-figure">
                            <img
                                src="/docs-images/azure-private-deployment-architecture.png"
                                alt="Azure private deployment architecture for the bug management and monitoring POC"
                            />
                            <figcaption>
                                Private Azure deployment architecture showing enterprise access through a private
                                Application Gateway, the private app tier, backend integration with Synapse, Data
                                Factory, Log Analytics, Azure OpenAI, Key Vault, Azure Container Registry, and private
                                endpoint access to ADLS Gen2 and platform services.
                            </figcaption>
                        </figure>
                        <div className="docs-card-grid">
                            {azureGuideOverviewCards.map((item) => (
                                <div key={item.title} className="docs-info-card">
                                    <h4>{item.title}</h4>
                                    <p>{item.details}</p>
                                </div>
                            ))}
                        </div>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">Resource Inventory</p>
                        <h3>Recommended Azure resources</h3>
                        <div className="table-wrap docs-table-wrap">
                            <table className="mapping-table">
                                <thead>
                                    <tr>
                                        <th>Resource Group</th>
                                        <th>Resource</th>
                                        <th>Proposed Name</th>
                                        <th>Purpose</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {azureResourceInventoryRows.map((row) => (
                                        <tr key={`${row.resource_group}-${row.resource}-${row.proposed_name}`}>
                                            <td>{row.resource_group}</td>
                                            <td>{row.resource}</td>
                                            <td>{row.proposed_name}</td>
                                            <td>{row.purpose}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">Network Layout</p>
                        <h3>Proposed VNet and subnet plan</h3>
                        <p className="hero-copy docs-copy">
                            The CIDRs below are proposed defaults for the POC, not hard Azure requirements. They give
                            the implementation team a clean starting point that can be adapted to enterprise IPAM.
                        </p>
                        <figure className="docs-figure">
                            <img
                                src="/docs-images/azure-vnet-subnet-layout.png"
                                alt="VNet and subnet layout for the private Azure deployment"
                            />
                            <figcaption>
                                Proposed VNet and subnet layout for the private deployment, showing dedicated address
                                space for the Application Gateway, Container Apps environment, private endpoints,
                                Bastion, VPN or ExpressRoute gateway, and inbound and outbound DNS Private Resolver
                                endpoints.
                            </figcaption>
                        </figure>
                        <div className="table-wrap docs-table-wrap">
                            <table className="mapping-table">
                                <thead>
                                    <tr>
                                        <th>Subnet</th>
                                        <th>CIDR</th>
                                        <th>Purpose</th>
                                        <th>Notes</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {azureNetworkLayoutRows.map((row) => (
                                        <tr key={`${row.subnet}-${row.cidr}`}>
                                            <td>{row.subnet}</td>
                                            <td>{row.cidr}</td>
                                            <td>{row.purpose}</td>
                                            <td>{row.notes}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">Private Access</p>
                        <h3>Private endpoints and DNS zones</h3>
                        <div className="table-wrap docs-table-wrap">
                            <table className="mapping-table">
                                <thead>
                                    <tr>
                                        <th>Target</th>
                                        <th>Private Endpoint(s)</th>
                                        <th>Private DNS Zone(s)</th>
                                        <th>Notes</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {azurePrivateAccessRows.map((row) => (
                                        <tr key={`${row.target}-${row.private_endpoints}`}>
                                            <td>{row.target}</td>
                                            <td>{row.private_endpoints}</td>
                                            <td>{row.dns_zones}</td>
                                            <td>{row.notes}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">Access Model</p>
                        <h3>RBAC and implementation notes</h3>
                        <div className="table-wrap docs-table-wrap">
                            <table className="mapping-table">
                                <thead>
                                    <tr>
                                        <th>Principal</th>
                                        <th>Scope</th>
                                        <th>Role(s)</th>
                                        <th>Notes</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {azureAccessModelRows.map((row) => (
                                        <tr key={`${row.principal}-${row.scope}`}>
                                            <td>{row.principal}</td>
                                            <td>{row.scope}</td>
                                            <td>{row.roles}</td>
                                            <td>{row.notes}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        <div className="docs-card-grid">
                            {azureImplementationNotes.map((item) => (
                                <div key={item.title} className="docs-info-card">
                                    <h4>{item.title}</h4>
                                    <p>{item.details}</p>
                                </div>
                            ))}
                        </div>
                    </article>
                </DocsAccordion>
            </section>
        </section>
    );
}

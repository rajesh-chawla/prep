# -------------------------------------------------------------------------------
# Practical FDE use cases: Top-K aggregation
# -------------------------------------------------------------------------------
#
# Top-K aggregation turns a high-volume event stream into a prioritized answer:
#
#     What is happening most often, to whom, where, and during which time window?
#
# The value is not merely counting. The value is helping an FDE identify the
# highest-impact pattern, retrieve representative traces, and choose the next
# investigation or remediation step.
#
# Core FDE use cases:
#
# 1. Customer incident monitoring
#    Group/count:
#        tenant_id, error_code, service, dependency, region, workflow
#
#    Question:
#        "Which final customer-visible failures are affecting this tenant most
#        during the incident window?"
#
#    Example output:
#        TOOL_TIMEOUT: 87
#        AUTHORIZATION_DENIED: 24
#        INVALID_TOOL_ARGUMENT: 6
#
#    FDE action:
#    - Start investigation with the dominant category.
#    - Retrieve representative trace IDs.
#    - Check deployment changes, dependency health, configuration, retries,
#      region correlation, and affected customer scope.
#
#    Important:
#    A high count identifies a pattern and investigation priority. It does not
#    prove root cause. TOOL_TIMEOUT may be caused by downstream latency, network
#    behavior, throttling, payload size, bad credentials, or retry amplification.
#
# 2. Data-ingestion quality
#    Group/count:
#        source system, schema version, validation failure category,
#        malformed-record reason, field name, reconciliation mismatch reason
#
#    Question:
#        "What is preventing customer/partner records from entering the system?"
#
#    Example output:
#        MISSING_CUSTOMER_ID: 14,240
#        INVALID_TIMESTAMP_FORMAT: 8,901
#        UNKNOWN_PRODUCT_SKU: 2,444
#        DUPLICATE_EXTERNAL_ORDER_ID: 731
#
#    FDE action:
#    - Identify broken source mappings or unsupported schema changes.
#    - Improve source-side validation, documentation, or onboarding guidance.
#    - Quarantine malformed records, repair/reprocess where safe, and track
#      the quality trend after a fix.
#
# 3. AI-agent and tool reliability
#    Group/count:
#        tool_name, error_category, failure_stage, model deployment,
#        connector, retry outcome, policy decision
#
#    Useful categories:
#        MODEL_OUTPUT_INVALID
#        TOOL_CALL_SCHEMA_INVALID
#        TOOL_AUTHORIZATION_DENIED
#        TOOL_TIMEOUT
#        RETRIEVAL_NO_AUTHORIZED_RESULTS
#        MAX_ITERATIONS_EXCEEDED
#        POLICY_REJECTED
#
#    Questions:
#    - Which tool fails most often for this tenant?
#    - Are failures due to model output, orchestration, retrieval, policy,
#      authorization, or a downstream dependency?
#    - Did failures increase after a tool, connector, prompt, or deployment change?
#
#    FDE action:
#    - Inspect traces for representative failures.
#    - Fix the integration, schema, timeout, retry behavior, or policy mapping.
#    - Validate that the remediation improves customer-visible outcomes.
#
# 4. RAG and retrieval quality
#    Group/count:
#        no_result_reason, source/connector, document collection/index,
#        authorization result, freshness band, query class
#
#    Questions:
#    - Are users receiving no results because content is missing, stale,
#      unauthorized, poorly indexed, or unavailable?
#    - Which source/connector produces the most retrieval failures?
#    - Are permission boundaries excluding content customers expect to see?
#
#    FDE action:
#    - Repair indexing, source connectivity, document permissions, chunking,
#      freshness handling, or retrieval ranking.
#
# 5. Support triage and customer health
#    Group/count:
#        customer-visible failure category, affected workflow, failing dependency,
#        support issue signature, severity level
#
#    Example customer-health summary:
#
#        Tenant: Contoso
#        Window: last 24 hours
#
#        Top customer-visible failures:
#        1. TOOL_TIMEOUT: 87
#        2. AUTHORIZATION_DENIED: 24
#        3. INVALID_TOOL_ARGUMENT: 6
#
#        Most affected workflow: invoice-resolution-agent
#        Most failing dependency: billing-api
#        Representative traces: trace-812, trace-935, trace-1102
#
#    FDE action:
#    - Give support a prioritized, tenant-scoped, trace-linked starting point.
#    - Route the issue to the correct product, platform, connector, or customer
#      team with evidence rather than vague symptoms.
#
# 6. Onboarding and product workflow friction
#    Group/count:
#        onboarding step, connector type, setup failure, integration version,
#        abandoned workflow stage, unsupported request category
#
#    Questions:
#    - At which onboarding step do customers fail most often?
#    - Which connector configuration produces the most setup errors?
#    - Which workflow stage has the largest customer drop-off?
#
#    FDE action:
#    - Improve UI, documentation, default configuration, validation feedback,
#      SDK behavior, and deployment guidance.
#
# 7. Release, regression, and SLA monitoring
#    Group/count:
#        build version, deployment ring, region, error category,
#        endpoint, latency bucket, dependency
#
#    Questions:
#    - Did this release introduce a new dominant error category?
#    - Which service, region, or endpoint has the most latency/SLA breaches?
#    - Did a canary deployment create a customer-visible regression?
#
#    FDE action:
#    - Pause rollout, rollback, mitigate, scale a dependency, or open a
#      targeted engineering investigation.
#
# 8. Cost, capacity, and reliability
#    Group/count:
#        tenant_id, model deployment, tool name, workflow, retry reason,
#        endpoint, dependency, latency bucket
#
#    Questions:
#    - Which workflows consume the most model tokens, tool calls, or API cost?
#    - Which retries are increasing load without improving final success?
#    - Which dependency is creating the largest latency/capacity problem?
#
#    FDE action:
#    - Optimize prompts, cache repeat work, route requests to a smaller model,
#      cap retries, tune timeouts, add quotas, or scale the bottleneck.
#
# 9. Security and policy enforcement
#    Group/count:
#        denied action type, policy rule, authorization failure,
#        tool/action name, identity category, suspicious event class
#
#    Questions:
#    - Which policy denials recur most often?
#    - Is a customer configuration or role mapping preventing valid actions?
#    - Are we seeing an unusual concentration of suspicious requests?
#
#    FDE action:
#    - Repair authorization configuration, improve policy feedback, investigate
#      abuse, rate-limit, or escalate according to the security process.
#
# -------------------------------------------------------------------------------
# FDE correctness and operational rules
# -------------------------------------------------------------------------------
#
# Before counting:
#
# - Scope to the authorized tenant/customer and the relevant time window.
# - Decide whether to count raw attempts, retries, final outcomes, or only
#   customer-visible unrecovered failures.
# - Normalize raw errors into stable categories such as TOOL_TIMEOUT or
#   AUTHORIZATION_DENIED. Avoid grouping by raw exception text, prompt text,
#   tool arguments, or other high-cardinality/sensitive values.
# - Deduplicate replayed messages or retries with event_id when the business
#   metric represents unique logical events rather than delivery attempts.
# - Keep representative trace IDs, timestamps, and correlation IDs so a Top-K
#   result leads to inspectable evidence rather than an unsupported conclusion.
#
# After counting:
#
# - Treat Top-K as an investigation-prioritization mechanism, not causal proof.
# - Link the dominant category to representative traces, dependency health,
#   deployment/configuration changes, customer context, and runbooks.
# - Turn the result into a clear next action: investigate, alert, ticket,
#   notify support, correct ingestion, pause a rollout, or execute a safe
#   approved remediation.
# - Measure whether the action improved final customer-visible outcomes.
#
# Summary:
#
#     Top-K aggregation
#         -> identifies the largest actionable pattern
#         -> narrows where an FDE begins investigation
#         -> connects telemetry to a customer-impacting action
#

# Production note:
# Counter is appropriate for a bounded in-memory batch. For a continuous event
# stream, use durable ingestion, time windows to bound state, partitioned
# aggregation, deduplication where required, checkpointed recovery, and
# materialized summaries for dashboards and support tooling.

from collections import Counter


events = [
    {"customer_id": "contoso", "event": "error"},
    {"customer_id": "fabrikam", "event": "error"},
    {"customer_id": "contoso", "event": "warning"},
    {"customer_id": "adventure-works", "event": "error"},
    {"customer_id": "contoso", "event": "error"},
    {"customer_id": "fabrikam", "event": "warning"},
]

k = 2


# Aggregate event counts by customer ID.
# In a production service, validate event shape and enforce tenant authorization
# outside or before this aggregation boundary.
customer_event_counts = Counter(
    event["customer_id"]
    for event in events
)

# Return up to K (customer_id, count) pairs ordered by descending frequency.
# Define an explicit secondary ordering if equal counts need stable customer-facing
# behavior beyond Counter's encounter ordering.
top_k_customers = customer_event_counts.most_common(k)

print("Customer event counts:", customer_event_counts)
print(f"Top {k} customers by event count:", top_k_customers)
# I expect a server-owned, versioned tool registry that defines 
# schemas, 
# ownership, 
# risk classification, 
# authorization scopes, 
# confirmation policy, 
# timeout/retry behavior, 
# audit requirements. 
# 
# The LLM may propose a structured call, but server-side layers must validate it, authorize the resolved user against the target resource, 
# and gate consequential writes with explicit confirmation. 
# 
# I expect a common versioned JSON error envelope for pre-execution validation and runtime failures, 
# using machine-readable codes, correlation IDs, retryability, and a violations array. 
# 
# The validator should return multiple independent actionable errors, while avoiding dependent checks 
# after a type/required-field failure and avoiding disclosure of sensitive security or internal details.”



# “I expect a versioned, server-owned tool registry with 
# tool ownership, 
# lifecycle state, 
# input/output schemas, 
# risk classification, 
# side-effect metadata, 
# auth scopes, 
# confirmation policy, 
# idempotency, 
# timeout/retry rules, 
# rate limits, 
# data classification, 
# environment/tenant availability, 
# cost limits, 
# trusted provenance. 
# 
# At runtime, calls should pass schema, business, authorization, and policy validation; 
# execute with least-privileged identities and concurrency/idempotency safeguards; 
# and have their outputs validated and sanitized before returning to the model. 
# The platform should support auditability, kill switches, controlled rollout, 
# schema-change detection, testing, monitoring, and a standard error contract.”

tool_calls = [
    {
        "tool_name": "get_order",
        "arguments": {
            "order_id": "order-1001",
        },
    },
    {
        "tool_name": "search_orders",
        "arguments": {
            "customer_id": "customer-77",
            "limit": 10,
        },
    },
    {
        "tool_name": "cancel_order",
        "arguments": {
            "order_id": "order-1002",
            "reason": "Customer requested cancellation",
        },
    },
]

# Valid Result
# {
#     "valid": True,
#     "tool_name": "get_order",
#     "errors": [],
# }
# Invalid Result
# {
#     "valid": False,
#     "tool_name": "search_orders",
#     "errors": [
#         "limit must be an integer between 1 and 100",
#     ],
# }

# FUNCTION validate_tool_call(tool_call):
def validate_tool_call(tool_call):
#     CREATE an empty list called errors
    errors = []

#     GET tool_name FROM tool_call
#     GET arguments FROM tool_call
    tool_name = tool_call["tool_name"]
    tool_args = tool_call["arguments"]

#     CREATE a list/set of allowed tool names:
#         get_order
#         search_orders 
#         cancel_order
    allowed_tool_names = set()
    for valid_tool_call in tool_calls:
        allowed_tool_names.add(valid_tool_call["tool_name"])

#     IF tool_name is not in allowed tool names:
#         ADD "tool is not allowed" to errors
#         RETURN validation result with valid=False and errors

    if tool_name not in allowed_tool_names:
        errors.append("Tool is not allowed")

#     IF arguments is not a dictionary:
#         ADD "arguments must be a dictionary" to errors
#         RETURN validation result with valid=False and errors

    if not isinstance(tool_args, dict):
        errors.append("Arguments must be a dictionary")

    if tool_name in allowed_tool_names:
        for a_tool in tool_calls:
            if tool_name == a_tool["tool_name"]:
                args_to_validate = a_tool["arguments"]
                if args_to_validate.keys() != tool_args.keys():
                    errors.append(f"Argument mismatch. Expected: {args_to_validate.keys()}, got {tool_args.keys()} ")
                    break
#     IF tool_name is "get_order":
#         # TODO:
#         # Verify exact allowed/required argument names.
#         # Verify order_id exists, is a string, is non-empty,
#         # and begins with "order-".

        if tool_name == "get_order":
            order_id_value = tool_args["order_id"]
            if not isinstance(order_id_value, str):
                errors.append("order_id must be a str for get_order call.")
            if len(order_id_value) == 0:
                errors.append("order_id must have a valuefor for get_order call.")
            if not order_id_value.startswith("order-"):
                errors.append("order_id must start with order- for get_order call.")

#     ELSE IF tool_name is "search_orders":
#         # TODO:
#         # Verify exact allowed/required argument names.
#         # Verify customer_id format.
#         # Verify limit is an integer from 1 through 100.

        if tool_name == "search_orders":
            customer_id_value = tool_args["customer_id"]
            if not isinstance(customer_id_value, str):
                errors.append("customer_id must be a str for search_orders call.")
            if len(customer_id_value) == 0:
                errors.append("customer_id must have a valuefor for search_orders call.")
            if not customer_id_value.startswith("customer-"):
                errors.append("customer_id must start with customer- for search_orders call.")
            limit_value = tool_args["limit"]
            if not isinstance(limit_value, int):
                errors.append("limit must be an int for search_orders call.")
            if limit_value < 1 or limit_value > 100:
                errors.append("limit must be be between 1 and 100 for search_orders call.")

#     ELSE IF tool_name is "cancel_order":
#         # TODO:
#         # Verify exact allowed/required argument names.
#         # Verify order_id format.
#         # Verify reason is a non-empty string of <= 500 characters.
#         #
#         # Important: valid input does NOT mean execute automatically.
#         # Mark this action as requiring confirmation/authorization.

        if tool_name == "cancel_order":
            order_id_value = tool_args["order_id"]
            if not isinstance(order_id_value, str):
                errors.append("order_id must be a str for cancel_order call.")
            if len(order_id_value) == 0:
                errors.append("order_id must have a value for for cancel_order call.")
            if not order_id_value.startswith("order-"):
                errors.append("order_id must start with order- for cancel_order call.")
            reason_value = tool_args["reason"]
            if not isinstance(reason_value, str):
                errors.append("reason must be a str for cancel_order call.")

            reason_value_len = len(reason_value)
            if (reason_value_len < 1 or reason_value_len > 500):
                errors.append("reason must be between 0 and 500 characters cancel_order call.")

#     RETURN a dictionary containing:
#         valid = whether errors is empty
#         tool_name
#         errors

    to_return = {}
    to_return["tool_name"] = tool_name
    to_return["errors"] = errors
    to_return["valid"] = True
    if (len(errors) > 0):
        to_return["valid"] = False

    return to_return


# Tests
valid_get = {
    "tool_name": "get_order",
    "arguments": {
        "order_id": "order-1001",
    },
}

invalid_tool = {
    "tool_name": "delete_database",
    "arguments": {},
}

invalid_limit = {
    "tool_name": "search_orders",
    "arguments": {
        "customer_id": "customer-77",
        "limit": 500,
    },
}

unexpected_argument = {
    "tool_name": "get_order",
    "arguments": {
        "order_id": "order-1001",
        "include_credit_card": True,
    },
}

invalid_cancel = {
    "tool_name": "cancel_order",
    "arguments": {
        "order_id": "order-1002",
        "reason": "",
    },
}
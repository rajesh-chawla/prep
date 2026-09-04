
"""
1. Receive user input
2. Construct a model request with:
   - system/developer instructions and safety policy
   - user request
   - selected prior conversation/workflow state
   - tool schemas and tool-use rules
3. Call the planner LLM
4. Inspect its response
5. If it contains a final answer:
   - validate/output-filter if needed
   - return it to the user
6. If it contains one or more tool calls:
   - validate the requested calls
   - authorize them for this user/tenant/context
   - execute permitted tools
   - record results and trace metadata
   - add tool results to context
   - return to Step 3
7. Stop on final answer, explicit stop, timeout, cancellation, policy denial,
   unrecoverable failure, or maximum-step limit
"""


"""
Agent Questions:

- How do you ground an agent in the correct user/tenant data?
- How do you make tools discoverable but safely scoped?
- How do you separate read, recommend, approve, and execute?
- How do you retain useful context without over-sharing sensitive data?
- How do you manage ongoing and background work?
- How do you make an agent’s actions observable, cancellable, and auditable?
- How do you handle browser/file/shell access without giving the model uncontrolled authority?
- How do you prevent repeated or unsafe side effects?
- How do you evaluate task completion, factual grounding, safety, latency, and cost?
"""

"""
Potential flow with welterHP:
Inbound email or Teams request
  ↓
Deterministic classification/routing prechecks:
  tenant, identity, sender, access, rate limits
  ↓
Single enrollment-operations agent:
  interprets request and proposes read-only evidence gathering
  ↓
Parallel deterministic retrieval:
  EVIPS record, document state, email thread, payer rules
  ↓
Single agent:
  synthesizes evidence and drafts a response/recommendation
  ↓
Deterministic policy node:
  read only? draft only? needs approval? may write?
  ↓
Human approval when required
  ↓
Deterministic email/EVIPS execution service
  ↓
Persist trace, audit record, result, metrics

"""

import time

SUCCESS = 0
TIMED_OUT = 1
FAILED_VALIDATION = 2
STOPPED = 3
FAILED_AUTHORIZATION = 4
MAX_STEPS_EXCEEDED = 5
RUNNING = 6
FAILED_TOOL = 7

def planner(request, context):
    get_customer_tool_call = {
        "kind": "tool_call",
        "call_id": "call-001",
        "tool_name": "get_customer",
        "arguments": {
            "customer_id": request["customer_id"]
        }
    }
    final_answer = {
        "kind": "final_answer",
        "answer": f"Customer results: {context[-1]}"
    }
    
    to_return = {}
    
    if (not context):
        to_return = get_customer_tool_call
    else:
        to_return = final_answer
    
    return to_return    
    
def run_tool(tool_name, arguments):
    get_customer_tool = {
        "ok": True,
        "result": {
            "customer_id": arguments["customer_id"],
            "status": "inactive"
        }
    }
    unknown_tool = {
        "ok": False,
        "error": "Unknown tool"
    }
    to_return = unknown_tool
    if tool_name == "get_customer":
        to_return = get_customer_tool
        
    return to_return
    
def run_loop(request, max_timeout = 10.0, max_steps = 10):
    trace = []
    context = []
    
    deadline = time.monotonic() + max_timeout
    
    to_return = {
        "return_code": RUNNING,
        "answer": None,
        "trace": trace
    }

    for step in range(max_steps):
        if time.monotonic() > deadline:
            to_return["return_code"] = TIMED_OUT
            return(to_return)

        decision = planner(request, context)

        if not isinstance(decision, dict):
            trace.append({
                "step": step,
                "event": "invalid_decision"
            })
            to_return["return_code"] = FAILED_VALIDATION
            return to_return

        if decision.get("kind") == "final_answer":
            trace.append({
                "step": step,
                "event": "final_answer"
            })
            to_return["return_code"] = SUCCESS
            to_return["answer"] = decision.get("answer")
            return(to_return)
        
        # Get the tool / arugments from the planner
        tool_name = decision.get("tool_name")
        arguments = decision.get("arguments")

        # validate tool name 
        # validate tool arguments
        
        # Invoke the tool        
        tool_result = run_tool(tool_name, arguments)

        if not tool_result["ok"] :
            trace.append({
                "step": step,
                "event": "tool_failed",
                "tool_name": tool_name,
                "error": tool_result["error"]
            })
            to_return["return_code"] = FAILED_TOOL
            return(to_return)

        # The tool succeeded, update the context for next run
        # Update trace for troubleshooting
        
        context.append(tool_result["result"])
        trace.append({
            "step": step,
            "event": "tool_succeeded",
            "tool_name": tool_name
        })
    to_return["return_code"] = MAX_STEPS_EXCEEDED
    return to_return
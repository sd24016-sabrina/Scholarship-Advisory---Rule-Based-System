import json
import operator

import pandas as pd
import streamlit as st

# =====================================================================
# 1. KNOWLEDGE BASE  (the rules given in the lab question, EXACTLY)
# =====================================================================
DEFAULT_RULES_JSON = """[
  {
    "name": "Top merit candidate",
    "priority": 100,
    "conditions": [
      ["cgpa", ">=", 3.7],
      ["co_curricular_score", ">=", 80],
      ["family_income", "<=", 8000],
      ["disciplinary_actions", "==", 0]
    ],
    "action": {
      "decision": "AWARD_FULL",
      "reason": "Excellent academic & co-curricular performance, with acceptable need"
    }
  },
  {
    "name": "Good candidate - partial scholarship",
    "priority": 80,
    "conditions": [
      ["cgpa", ">=", 3.3],
      ["co_curricular_score", ">=", 60],
      ["family_income", "<=", 12000],
      ["disciplinary_actions", "<=", 1]
    ],
    "action": {
      "decision": "AWARD_PARTIAL",
      "reason": "Good academic & involvement record with moderate need"
    }
  },
  {
    "name": "Need-based review",
    "priority": 70,
    "conditions": [
      ["cgpa", ">=", 2.5],
      ["family_income", "<=", 4000]
    ],
    "action": {
      "decision": "REVIEW",
      "reason": "High need but borderline academic score"
    }
  },
  {
    "name": "Low CGPA – not eligible",
    "priority": 95,
    "conditions": [
      ["cgpa", "<", 2.5]
    ],
    "action": {
      "decision": "REJECT",
      "reason": "CGPA below minimum scholarship requirement"
    }
  },
  {
    "name": "Serious disciplinary record",
    "priority": 90,
    "conditions": [
      ["disciplinary_actions", ">=", 2]
    ],
    "action": {
      "decision": "REJECT",
      "reason": "Too many disciplinary records"
    }
  }
]"""

# Facts (applicant attributes) that a rule is allowed to use
FACT_FIELDS = [
    "cgpa",
    "family_income",
    "co_curricular_score",
    "community_service_hours",
    "semester",
    "disciplinary_actions",
]

# Comparison operators a rule condition can use
OPERATORS = {
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
    "==": operator.eq,
    "!=": operator.ne,
}

# =====================================================================
# 2. INFERENCE ENGINE  (match -> resolve conflict -> act)
# =====================================================================


def validate_rules(rules):
    """Check the structure of the rule list. Returns a list of error messages."""
    errors = []
    if not isinstance(rules, list) or len(rules) == 0:
        return ["Rules must be a non-empty JSON list [ ... ]."]

    for i, rule in enumerate(rules, start=1):
        label = f"Rule #{i}"
        if not isinstance(rule, dict):
            errors.append(f"{label}: must be a JSON object.")
            continue

        for key in ("name", "priority", "conditions", "action"):
            if key not in rule:
                errors.append(f"{label}: missing key '{key}'.")

        if "priority" in rule and (
            isinstance(rule["priority"], bool)
            or not isinstance(rule["priority"], (int, float))
        ):
            errors.append(f"{label}: 'priority' must be a number.")

        conditions = rule.get("conditions", [])
        if not isinstance(conditions, list) or len(conditions) == 0:
            errors.append(f"{label}: 'conditions' must be a non-empty list.")
        else:
            for cond in conditions:
                if not isinstance(cond, list) or len(cond) != 3:
                    errors.append(f"{label}: condition {cond} must be [field, operator, value].")
                    continue
                field, op, value = cond
                if field not in FACT_FIELDS:
                    errors.append(f"{label}: unknown field '{field}'. Allowed: {', '.join(FACT_FIELDS)}.")
                if op not in OPERATORS:
                    errors.append(f"{label}: unknown operator '{op}'. Allowed: {', '.join(OPERATORS)}.")
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    errors.append(f"{label}: value in {cond} must be a number.")

        action = rule.get("action", {})
        if not isinstance(action, dict) or "decision" not in action or "reason" not in action:
            errors.append(f"{label}: 'action' must contain 'decision' and 'reason'.")

    return errors


def evaluate_rule(rule, facts):
    """Test one rule against the applicant's facts.
    Returns (fired, details) where details lists every condition's result."""
    details = []
    for field, op, value in rule["conditions"]:
        actual = facts[field]
        passed = OPERATORS[op](actual, value)
        details.append(
            {
                "condition": f"{field} {op} {value}",
                "applicant value": actual,
                "result": "PASS" if passed else "FAIL",
            }
        )
    fired = all(d["result"] == "PASS" for d in details)  # AND logic
    return fired, details


def run_engine(rules, facts):
    """Forward chaining (data-driven) with priority-based conflict resolution.
    1. MATCH   : check every rule against the facts.
    2. RESOLVE : among the rules that matched, pick the highest priority.
    3. ACT     : return that rule's decision and reason.
    """
    ordered = sorted(rules, key=lambda r: r["priority"], reverse=True)

    trace = []
    matched = []
    for rule in ordered:
        fired, details = evaluate_rule(rule, facts)
        trace.append({"rule": rule, "fired": fired, "details": details})
        if fired:
            matched.append(rule)

    if matched:
        winner = matched[0]  # highest priority because the list is sorted
        result = {
            "decision": winner["action"]["decision"],
            "reason": winner["action"]["reason"],
            "rule_name": winner["name"],
            "priority": winner["priority"],
        }
    else:
        result = {
            "decision": "NO_MATCH",
            "reason": "No rule matched this applicant. Refer to the committee for manual review.",
            "rule_name": "-",
            "priority": "-",
        }
    return result, trace, matched


# =====================================================================
# 3. USER INTERFACE (Streamlit)
# =====================================================================
st.set_page_config(page_title="Scholarship Advisory System", layout="wide")

st.title("Scholarship Advisory - Rule-Based System")
st.caption(
    "BSD3513 Lab Report 3 | Knowledge Representation: facts + IF-THEN rules + inference engine. "
    "Edit the rules in the 'Rule Editor' tab and re-evaluate."
)

# Keep the JSON text in session state so edits are not lost when the app reruns
if "rules_text" not in st.session_state:
    st.session_state["rules_text"] = DEFAULT_RULES_JSON


def reset_rules():
    st.session_state["rules_text"] = DEFAULT_RULES_JSON


tab_eval, tab_rules = st.tabs(["Evaluate Applicant", "Rule Editor (JSON)"])

# ---------- Rule editor tab (runs first so 'rules' is ready for evaluation) ----------
rules = None
with tab_rules:
    st.subheader("Rule Base (JSON)")
    st.write(
        "Each rule has a **name**, **priority** (higher is checked first), "
        "**conditions** (all must be true) and an **action** (decision + reason)."
    )
    st.write(
        "Allowed fields: `" + "`, `".join(FACT_FIELDS) + "`  |  "
        "Allowed operators: `" + "`, `".join(OPERATORS) + "`"
    )
    st.text_area("Edit the rules here:", key="rules_text", height=480)
    st.button("Reset to lecturer's rules", on_click=reset_rules)

    try:
        parsed = json.loads(st.session_state["rules_text"])
        problems = validate_rules(parsed)
        if problems:
            st.error("Rule configuration has problems:")
            for p in problems:
                st.write("- " + p)
        else:
            rules = parsed
            st.success(f"Rules are valid ({len(rules)} rules loaded)")
    except json.JSONDecodeError as err:
        st.error(f"Invalid JSON: {err}")

# ---------- Evaluation tab ----------
with tab_eval:
    st.subheader("Applicant Facts")

    col1, col2, col3 = st.columns(3)
    with col1:
        cgpa = st.number_input("Cumulative GPA (CGPA)", 0.00, 4.00, 3.50, 0.01)
        family_income = st.number_input("Monthly family income (RM)", 0.0, 100000.0, 5000.0, 100.0)
    with col2:
        co_curricular_score = st.slider("Co-curricular involvement score (0–100)", 0, 100, 70)
        community_service_hours = st.number_input("Community service hours", 0, 1000, 20, 1)
    with col3:
        semester = st.number_input("Current semester of study", 1, 14, 4, 1)
        disciplinary_actions = st.number_input("Number of disciplinary actions", 0, 20, 0, 1)

    facts = {
        "cgpa": float(cgpa),
        "family_income": float(family_income),
        "co_curricular_score": int(co_curricular_score),
        "community_service_hours": int(community_service_hours),
        "semester": int(semester),
        "disciplinary_actions": int(disciplinary_actions),
    }

    if st.button("Evaluate Applicant", type="primary"):
        if rules is None:
            st.error("Please fix the rules in the 'Rule Editor (JSON)' tab first.")
        else:
            result, trace, matched = run_engine(rules, facts)

            st.subheader("Decision")
            message = (
                f"**{result['decision']}**  \n"
                f"Reason: {result['reason']}  \n"
                f"Rule fired: {result['rule_name']} (priority {result['priority']})"
            )
            if result["decision"] == "AWARD_FULL":
                st.success(message)
            elif result["decision"] == "AWARD_PARTIAL":
                st.info(message)
            elif result["decision"] in ("REVIEW", "NO_MATCH"):
                st.warning(message)
            else:
                st.error(message)

            if len(matched) > 1:
                names = ", ".join(f"{r['name']} ({r['priority']})" for r in matched)
                st.caption(
                    f"{len(matched)} rules matched: {names}. "
                    "The highest-priority rule was used (conflict resolution)."
                )

            st.subheader("Rule Evaluation Summary")
            summary = pd.DataFrame(
                [
                    {
                        "Priority": t["rule"]["priority"],
                        "Rule": t["rule"]["name"],
                        "Decision if fired": t["rule"]["action"]["decision"],
                        "Matched?": "YES" if t["fired"] else "no",
                    }
                    for t in trace
                ]
            )
            st.dataframe(summary, use_container_width=True, hide_index=True)

            st.subheader("Why? (condition-by-condition explanation)")
            for t in trace:
                icon = "[MATCHED]" if t["fired"] else "[not matched]"
                with st.expander(f"{icon} {t['rule']['name']} (priority {t['rule']['priority']})"):
                    st.dataframe(pd.DataFrame(t["details"]), use_container_width=True, hide_index=True)

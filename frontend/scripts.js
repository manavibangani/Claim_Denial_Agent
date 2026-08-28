const apiBaseUrl = "http://127.0.0.1:8000";

const NOT_APPLICABLE = "Not applicable for this case";

function setText(id, value, fallback = "N/A") {
    document.getElementById(id).innerText =
        value === undefined || value === null || value === "" ? fallback : value;
}

function formatList(items) {
    return Array.isArray(items) && items.length ? items.join(", ") : "None";
}

async function analyzeClaim() {
    const claimId = document.getElementById("claimId").value.trim();
    const statusBar = document.getElementById("statusBar");

    if (!claimId) {
        statusBar.innerText = "Enter a claim ID to start analysis";
        return;
    }

    statusBar.innerText = "Analyzing denial reason and routing workflow...";

    try {
        const response = await fetch(`${apiBaseUrl}/analyze-claim/${claimId}`);
        const data = await response.json();

        if (data.error) {
            statusBar.innerText = data.error;
            return;
        }

        setText("patientName", data.patient_name);
        setText("claimAmount", data.claim_amount);
        setText("policyType", data.policy_type);
        setText("processedAt", data.processed_at);
        setText("denialReason", data.denial_reason);
        setText("decisionCategory", data.decision_category);
        // carc_code/carc_description are null when the LLM couldn't map the
        // denial reason to a known CARC category (routed to manual review instead).
        setText("carcCode", data.carc_code, NOT_APPLICABLE);
        setText("carcDescription", data.carc_description, NOT_APPLICABLE);
        setText("priorityLevel", data.priority_level);
        setText("toolUsed", data.tool_used);
        setText("llmReasoning", data.llm_reasoning);
        setText("agentActionStatus", data.agent_action_status);
        // escalation_queue is null when the case is handled automatically
        // (no human queue involved), e.g. an appeal letter was auto-drafted.
        setText("escalationQueue", data.escalation_queue, NOT_APPLICABLE);
        setText(
            "humanIntervention",
            data.human_intervention_required ? "Required" : "Not required"
        );
        setText("riskFlags", formatList(data.risk_flags));
        setText("complexityReasons", formatList(data.complexity_reasons));
        setText("analysis", data.ai_analysis, "No analysis available");
        setText("agentAction", data.agent_action_result);

        // appeal_letter is only present when the agent routed this claim to
        // draft_appeal_letter - e.g. not for fraud escalations or duplicate
        // checks. Keep the section visible either way so it's clear the field
        // was checked, not just missing from the page.
        setText("appealLetter", data.appeal_letter, NOT_APPLICABLE);

        statusBar.innerText = data.human_intervention_required
            ? "Complex case routed for human intervention"
            : "Automated workflow completed";
    } catch (error) {
        statusBar.innerText = "Unable to reach the claim agent API";
    }
}

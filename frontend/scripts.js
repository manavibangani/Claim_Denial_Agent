const apiBaseUrl = "http://127.0.0.1:8000";

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
        setText("priorityLevel", data.priority_level);
        setText(
            "automationConfidence",
            `${Math.round((data.automation_confidence || 0) * 100)}%`
        );
        setText("workflowAction", data.workflow_action);
        setText("nextStep", data.next_step);
        setText("agentActionStatus", data.agent_action_status);
        setText("escalationQueue", data.escalation_queue || "None");
        setText(
            "humanIntervention",
            data.human_intervention_required ? "Required" : "Not required"
        );
        setText("riskFlags", formatList(data.risk_flags));
        setText("complexityReasons", formatList(data.complexity_reasons));
        setText("analysis", data.ai_analysis, "No analysis available");
        setText("agentAction", data.agent_action_result);

        statusBar.innerText = data.human_intervention_required
            ? "Complex case routed for human intervention"
            : "Automated workflow completed";
    } catch (error) {
        statusBar.innerText = "Unable to reach the claim agent API";
    }
}

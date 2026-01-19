// abdm-status.js - ABDM Status Monitoring

let refreshInterval;
let webhookQueue = [];

// Initialize page
document.addEventListener("DOMContentLoaded", function () {
  // Load status data
  loadAllStatus();

  // Event listeners
  document
    .getElementById("testConnectionBtn")
    .addEventListener("click", testGatewayConnection);
  document
    .getElementById("refreshBridgeBtn")
    .addEventListener("click", refreshBridgeStatus);
  document
    .getElementById("clearQueueBtn")
    .addEventListener("click", clearWebhookQueue);
  document
    .getElementById("refreshLogBtn")
    .addEventListener("click", loadWebhookLog);

  // Auto-refresh every 15 seconds
  refreshInterval = setInterval(loadAllStatus, 15000);
});

// Clean up on page unload
window.addEventListener("beforeunload", function () {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
});

// Load all status data
async function loadAllStatus() {
  await Promise.all([
    checkGatewayStatus(),
    loadBridgeStatus(),
    loadWebhookQueue(),
    loadActiveConsents(),
    loadWebhookLog(),
  ]);
}

// Check gateway status
async function checkGatewayStatus() {
  try {
    const response = await fetch("http://127.0.0.1:8000/health", {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (response.ok) {
      document.getElementById("gatewayStatus").innerHTML =
        '<span class="status-dot status-online"></span> Online';
      document.getElementById("lastHealthCheck").textContent =
        new Date().toLocaleTimeString();
    } else {
      document.getElementById("gatewayStatus").innerHTML =
        '<span class="status-dot status-offline"></span> Error';
    }
  } catch (error) {
    document.getElementById("gatewayStatus").innerHTML =
      '<span class="status-dot status-offline"></span> Offline';
    document.getElementById("lastHealthCheck").textContent = "Failed";
  }
}

// Load bridge status
async function loadBridgeStatus() {
  try {
    // Try to get bridge info from gateway
    const authResponse = await fetch("http://127.0.0.1:8000/api/auth/session", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "REQUEST-ID": utils.generateUUID(),
        TIMESTAMP: new Date().toISOString(),
        "X-CM-ID": "sbx",
      },
      body: JSON.stringify({
        clientId: "client-001",
        clientSecret: "secret-001",
        grantType: "client_credentials",
      }),
    });

    if (authResponse.ok) {
      const authData = await authResponse.json();

      // Get bridge list
      const bridgeResponse = await fetch(
        "http://127.0.0.1:8000/api/bridge/list",
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${authData.accessToken}`,
          },
        },
      );

      if (bridgeResponse.ok) {
        const bridgeData = await bridgeResponse.json();
        const bridgeCount = bridgeData.bridges ? bridgeData.bridges.length : 0;
        document.getElementById("bridgeStatus").innerHTML =
          `${bridgeCount} Active`;
        document.getElementById("authStatus").innerHTML =
          '<span class="badge bg-success">Authenticated</span>';
      } else {
        document.getElementById("bridgeStatus").innerHTML =
          '<span class="text-danger">Error</span>';
        document.getElementById("authStatus").innerHTML =
          '<span class="badge bg-danger">Failed</span>';
      }
    } else {
      document.getElementById("bridgeStatus").innerHTML =
        '<span class="text-danger">Auth Failed</span>';
      document.getElementById("authStatus").innerHTML =
        '<span class="badge bg-danger">Failed</span>';
    }
  } catch (error) {
    document.getElementById("bridgeStatus").innerHTML =
      '<span class="text-danger">Unavailable</span>';
    document.getElementById("authStatus").innerHTML =
      '<span class="badge bg-secondary">Error</span>';
  }
}

// Load webhook queue
async function loadWebhookQueue() {
  try {
    const queue = await api.webhooks.getQueue();
    webhookQueue = Array.isArray(queue) ? queue : [];

    document.getElementById("pendingWebhooks").textContent =
      webhookQueue.length;

    const queueContent = document.getElementById("webhookQueueContent");

    if (webhookQueue.length === 0) {
      queueContent.innerHTML =
        '<div class="text-center text-muted"><i class="fas fa-inbox"></i> No pending webhooks</div>';
      return;
    }

    queueContent.innerHTML = webhookQueue
      .map((webhook, index) => {
        const typeClass = getWebhookTypeClass(webhook.type);
        return `
                <div class="card mb-2">
                    <div class="card-body p-2">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <span class="badge ${typeClass}">${webhook.type || "Unknown"}</span>
                                <small class="text-muted ms-2">${utils.formatDate(webhook.received_at)}</small>
                            </div>
                            <button class="btn btn-sm btn-outline-primary" onclick="viewWebhookDetails(${index})">
                                <i class="fas fa-eye"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
      })
      .join("");
  } catch (error) {
    console.error("Failed to load webhook queue:", error);
    document.getElementById("pendingWebhooks").textContent = "0";
    document.getElementById("webhookQueueContent").innerHTML =
      '<div class="text-center text-muted"><i class="fas fa-inbox"></i> Webhook service unavailable</div>';
  }
}

// Load active consents (placeholder - may need backend support)
async function loadActiveConsents() {
  // This would need a consent tracking endpoint in the backend
  // For now, set to placeholder
  document.getElementById("activeConsents").textContent = "0";
}

// Load webhook log (last 24 hours)
async function loadWebhookLog() {
  try {
    const queue = await api.webhooks.getQueue();
    const queueArray = Array.isArray(queue) ? queue : [];

    const tbody = document.getElementById("webhookLogTableBody");

    if (queueArray.length === 0) {
      tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted">
                        <i class="fas fa-inbox"></i> No webhook activity in the last 24 hours
                    </td>
                </tr>
            `;
      return;
    }

    tbody.innerHTML = queueArray
      .map((webhook, index) => {
        const typeClass = getWebhookTypeClass(webhook.type);
        const statusClass = webhook.processed ? "bg-success" : "bg-warning";
        const patientId =
          webhook.data?.patientId || webhook.data?.patient_id || "N/A";

        return `
                <tr>
                    <td>${utils.formatDate(webhook.received_at)}</td>
                    <td><span class="badge ${typeClass}">${webhook.type || "Unknown"}</span></td>
                    <td>${webhook.event || "N/A"}</td>
                    <td>${patientId}</td>
                    <td><span class="badge ${statusClass}">${webhook.processed ? "Processed" : "Pending"}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="viewWebhookDetails(${index})">
                            <i class="fas fa-eye"></i> View
                        </button>
                    </td>
                </tr>
            `;
      })
      .join("");
  } catch (error) {
    console.error("Failed to load webhook log:", error);
    document.getElementById("webhookLogTableBody").innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted">
                    <i class="fas fa-inbox"></i> Webhook service unavailable
                </td>
            </tr>
        `;
  }
}

// Get webhook type badge class
function getWebhookTypeClass(type) {
  const typeMap = {
    "data-request": "bg-primary",
    "data-delivery": "bg-success",
    consent: "bg-info",
    linking: "bg-warning",
    notification: "bg-secondary",
  };
  return typeMap[type?.toLowerCase()] || "bg-secondary";
}

// Test gateway connection
async function testGatewayConnection() {
  utils.showLoading();

  try {
    // Test health endpoint
    const healthResponse = await fetch("http://127.0.0.1:8000/health");

    if (!healthResponse.ok) {
      throw new Error("Gateway health check failed");
    }

    // Test authentication
    const authResponse = await fetch("http://127.0.0.1:8000/api/auth/session", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "REQUEST-ID": utils.generateUUID(),
        TIMESTAMP: new Date().toISOString(),
        "X-CM-ID": "sbx",
      },
      body: JSON.stringify({
        clientId: "client-001",
        clientSecret: "secret-001",
        grantType: "client_credentials",
      }),
    });

    if (!authResponse.ok) {
      throw new Error("Authentication failed");
    }

    const authData = await authResponse.json();

    utils.showSuccess(
      "Gateway connection successful! Token: " +
        authData.accessToken.substring(0, 20) +
        "...",
    );

    // Refresh status
    await loadAllStatus();
  } catch (error) {
    utils.showError("Connection test failed: " + error.message);
  } finally {
    utils.hideLoading();
  }
}

// Refresh bridge status
async function refreshBridgeStatus() {
  utils.showLoading();

  try {
    await loadBridgeStatus();
    utils.showSuccess("Bridge status refreshed");
  } catch (error) {
    utils.showError("Failed to refresh bridge status: " + error.message);
  } finally {
    utils.hideLoading();
  }
}

// Clear webhook queue
async function clearWebhookQueue() {
  if (!confirm("Are you sure you want to clear all webhooks from the queue?")) {
    return;
  }

  utils.showLoading();

  try {
    await api.webhooks.clearQueue();
    utils.showSuccess("Webhook queue cleared");
    await loadWebhookQueue();
    await loadWebhookLog();
  } catch (error) {
    utils.showError("Failed to clear webhook queue: " + error.message);
  } finally {
    utils.hideLoading();
  }
}

// View webhook details
function viewWebhookDetails(index) {
  if (index >= webhookQueue.length) {
    utils.showError("Webhook not found");
    return;
  }

  const webhook = webhookQueue[index];

  // Populate modal
  document.getElementById("detailWebhookId").textContent = webhook.id || index;
  document.getElementById("detailWebhookType").textContent =
    webhook.type || "Unknown";
  document.getElementById("detailWebhookType").className =
    "badge " + getWebhookTypeClass(webhook.type);
  document.getElementById("detailReceivedAt").textContent = utils.formatDate(
    webhook.received_at,
  );
  document.getElementById("detailWebhookStatus").textContent = webhook.processed
    ? "Processed"
    : "Pending";
  document.getElementById("detailWebhookStatus").className =
    "badge " + (webhook.processed ? "bg-success" : "bg-warning");
  document.getElementById("detailWebhookPayload").textContent = JSON.stringify(
    webhook.data || webhook,
    null,
    2,
  );

  // Show modal
  const modal = new bootstrap.Modal(
    document.getElementById("webhookDetailsModal"),
  );
  modal.show();
}

// Make function globally accessible
window.viewWebhookDetails = viewWebhookDetails;

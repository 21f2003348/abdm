// Dashboard functionality
document.addEventListener("DOMContentLoaded", async function () {
  await loadDashboardData();

  // Refresh data every 30 seconds
  setInterval(loadDashboardData, 30000);
});

async function loadDashboardData() {
  try {
    // Load statistics
    await Promise.all([
      loadPatientCount(),
      loadVisitCount(),
      loadCareContextCount(),
      checkABDMStatus(),
      loadRecentPatients(),
      loadWebhookNotifications(),
    ]);
  } catch (error) {
    console.error("Error loading dashboard data:", error);
  }
}

async function loadPatientCount() {
  try {
    const patients = await api.patients.list();
    console.log("Patients response:", patients);
    console.log("Is array?", Array.isArray(patients));
    const count = Array.isArray(patients)
      ? patients.length
      : patients?.length || 0;
    console.log("Patient count:", count);
    document.getElementById("totalPatients").textContent = count;
  } catch (error) {
    console.error("Error loading patient count:", error);
    document.getElementById("totalPatients").textContent = "0";
  }
}

async function loadVisitCount() {
  try {
    const visits = await api.visits.list();
    document.getElementById("activeVisits").textContent =
      (Array.isArray(visits) ? visits.length : visits?.length) || 0;
  } catch (error) {
    document.getElementById("activeVisits").textContent = "0";
  }
}

async function loadCareContextCount() {
  try {
    // This would need a specific endpoint - for now use placeholder
    document.getElementById("careContexts").textContent = "-";
  } catch (error) {
    document.getElementById("careContexts").textContent = "0";
  }
}

async function checkABDMStatus() {
  const statusElement = document.getElementById("abdmStatus");
  const statusCard = statusElement.closest(".card");

  try {
    const health = await api.healthCheck();
    if (health.status === "ok") {
      // Check gateway
      try {
        const gatewayHealth = await api.gatewayHealthCheck();
        if (gatewayHealth.status === "ok") {
          statusElement.innerHTML =
            '<span class="status-dot online"></span>Connected';
          statusCard.classList.remove("bg-warning", "bg-danger");
          statusCard.classList.add("bg-success");
        } else {
          throw new Error("Gateway not responding");
        }
      } catch {
        statusElement.innerHTML =
          '<span class="status-dot offline"></span>Gateway Down';
        statusCard.classList.remove("bg-success", "bg-warning");
        statusCard.classList.add("bg-danger");
      }
    }
  } catch (error) {
    statusElement.innerHTML = '<span class="status-dot offline"></span>Offline';
    statusCard.classList.remove("bg-success", "bg-warning");
    statusCard.classList.add("bg-danger");
  }
}

async function loadRecentPatients() {
  const container = document.getElementById("recentPatients");

  try {
    const patients = await api.patients.list();
    const patientList = Array.isArray(patients)
      ? patients
      : patients?.patients || [];

    if (patientList.length === 0) {
      container.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="fas fa-users fa-3x mb-2"></i>
                    <p>No patients registered yet</p>
                    <a href="patients.html" class="btn btn-sm btn-primary">Register First Patient</a>
                </div>
            `;
      return;
    }

    // Show last 5 patients
    const recentPatients = patientList.slice(-5).reverse();
    container.innerHTML = recentPatients
      .map(
        (patient) => `
            <a href="patients.html?id=${patient.patientId}" class="list-group-item list-group-item-action">
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1"><i class="fas fa-user text-primary"></i> ${patient.name}</h6>
                    <small class="text-muted">${patient.mobile}</small>
                </div>
                <small class="text-muted">
                    ${patient.abhaId ? `<span class="badge bg-success">ABHA: ${patient.abhaId}</span>` : '<span class="badge bg-secondary">No ABHA</span>'}
                </small>
            </a>
        `,
      )
      .join("");
  } catch (error) {
    container.innerHTML = `
            <div class="alert alert-danger mb-0">
                <i class="fas fa-exclamation-triangle"></i> Error loading patients
            </div>
        `;
  }
}

async function loadWebhookNotifications() {
  const container = document.getElementById("webhookNotifications");

  try {
    const webhooks = await api.webhooks.getQueue();
    const webhookArray = Array.isArray(webhooks) ? webhooks : [];

    if (webhookArray.length === 0) {
      container.innerHTML = `
                <div class="alert alert-info mb-0">
                    <i class="fas fa-inbox"></i> No recent webhook activity
                </div>
            `;
      return;
    }

    // Show last 3 webhooks
    const recentWebhooks = webhookArray.slice(-3).reverse();
    container.innerHTML = recentWebhooks
      .map(
        (webhook) => `
            <div class="alert alert-success mb-2">
                <small>
                    <i class="fas fa-check-circle"></i>
                    <strong>${webhook.type || "Webhook"}</strong> received
                    <br>
                    <span class="text-muted">${utils.formatDate(webhook.receivedAt)}</span>
                </small>
            </div>
        `,
      )
      .join("");
  } catch (error) {
    container.innerHTML = "";
  }
}

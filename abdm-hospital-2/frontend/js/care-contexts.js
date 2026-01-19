// care-contexts.js - Care Contexts Management

let currentContext = null;
let allCareContexts = [];

// Initialize page
document.addEventListener("DOMContentLoaded", function () {
  // Load care contexts
  loadCareContexts();

  // Event listeners
  document
    .getElementById("createCareContextForm")
    .addEventListener("submit", handleCreateCareContext);
  document
    .getElementById("searchPatientLink")
    .addEventListener("click", (e) => {
      e.preventDefault();
      const modal = new bootstrap.Modal(
        document.getElementById("patientSearchModal"),
      );
      modal.show();
    });
  document
    .getElementById("searchPatientBtn")
    .addEventListener("click", handleSearchPatient);
  document
    .getElementById("applyFiltersBtn")
    .addEventListener("click", applyFilters);
  document
    .getElementById("clearFiltersBtn")
    .addEventListener("click", clearFilters);
  document
    .getElementById("addHealthRecordBtn")
    .addEventListener("click", addHealthRecordForContext);

  // Check for URL params
  const urlParams = new URLSearchParams(window.location.search);
  const patientId = urlParams.get("patient_id");
  const visitId = urlParams.get("visit_id");

  if (patientId) {
    document.getElementById("patientId").value = patientId;
    document.getElementById("filterPatientId").value = patientId;
  }
  if (visitId) {
    document.getElementById("visitId").value = visitId;
  }
});

// Load all care contexts
async function loadCareContexts() {
  try {
    utils.showLoading();

    // Try to get care contexts from API
    // Note: You may need to implement a list endpoint for care contexts
    // For now, we'll try to get by patient if filtered
    const filterPatientId = document.getElementById("filterPatientId").value;

    let careContexts = [];
    if (filterPatientId) {
      careContexts = await api.careContexts.getByPatient(filterPatientId);
    } else {
      // If no filter, try to get all (may need backend support)
      try {
        const response = await api.get("/api/care-context/list");
        careContexts = response.care_contexts || [];
      } catch (error) {
        console.log("List endpoint not available, showing empty list");
        careContexts = [];
      }
    }

    allCareContexts = careContexts;
    renderCareContextsTable(careContexts);
  } catch (error) {
    utils.showError("Failed to load care contexts: " + error.message);
    document.getElementById("careContextsTableBody").innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-danger">
                    <i class="fas fa-exclamation-triangle"></i> Failed to load care contexts
                </td>
            </tr>
        `;
  } finally {
    utils.hideLoading();
  }
}

// Render care contexts table
function renderCareContextsTable(careContexts) {
  const tbody = document.getElementById("careContextsTableBody");
  document.getElementById("contextCount").textContent = careContexts.length;

  if (careContexts.length === 0) {
    tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted">
                    <i class="fas fa-inbox"></i> No care contexts found. Create one above or filter by patient ID.
                </td>
            </tr>
        `;
    return;
  }

  tbody.innerHTML = careContexts
    .map((context) => {
      const statusClass = getLinkingStatusClass(context.linking_status);
      const statusText = context.linking_status || "unknown";

      return `
            <tr>
                <td>${context.context_id || context.id}</td>
                <td>
                    <div>${context.patient_name || "N/A"}</div>
                    <small class="text-muted">${context.patient_id}</small>
                </td>
                <td>${context.context_name}</td>
                <td><span class="badge bg-info">${context.context_type || "N/A"}</span></td>
                <td>${context.visit_id || "N/A"}</td>
                <td><span class="badge ${statusClass}">${statusText}</span></td>
                <td>${utils.formatDate(context.created_at)}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="viewCareContext('${context.context_id || context.id}')">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            </tr>
        `;
    })
    .join("");
}

// Get linking status badge class
function getLinkingStatusClass(status) {
  const statusMap = {
    linked: "bg-success",
    pending: "bg-warning",
    failed: "bg-danger",
    unknown: "bg-secondary",
  };
  return statusMap[status?.toLowerCase()] || "bg-secondary";
}

// Handle create care context form submission
async function handleCreateCareContext(e) {
  e.preventDefault();

  // Simple validation
  const patientId = document.getElementById("patientId").value.trim();
  const contextType = document.getElementById("contextType").value;
  const contextName = document.getElementById("contextName").value.trim();

  if (!patientId || !contextType || !contextName) {
    utils.showError("Please fill in all required fields");
    return;
  }

  try {
    utils.showLoading();

    // Simple API call
    const result = await api.careContexts.createAndLink({
      patientId,
      contextType,
      contextName,
      description: document.getElementById("description").value.trim() || null,
    });

    if (result.status === "success" || result.linking_status === "linked") {
      utils.showSuccess("Care context created and linked successfully!");
    } else if (result.linking_status === "pending") {
      utils.showToast("Care context created. Linking is pending.", "warning");
    } else {
      utils.showToast("Care context created but linking failed", "warning");
    }

    e.target.reset();
    await loadCareContexts();
  } catch (error) {
    utils.showError("Failed to create care context: " + error.message);
  } finally {
    utils.hideLoading();
  }
}

// Handle patient search
async function handleSearchPatient() {
  const mobile = document.getElementById("searchMobile").value;

  if (!mobile || mobile.length !== 10) {
    utils.showError("Please enter a valid 10-digit mobile number");
    return;
  }

  try {
    utils.showLoading();
    const patient = await api.patients.search(mobile);

    if (patient) {
      document.getElementById("searchResults").innerHTML = `
                <div class="card">
                    <div class="card-body">
                        <h6>${patient.name}</h6>
                        <p class="mb-2">
                            <strong>Patient ID:</strong> ${patient.patient_id}<br>
                            <strong>Mobile:</strong> ${patient.mobile_number}<br>
                            <strong>ABHA ID:</strong> ${patient.abha_id || "Not available"}
                        </p>
                        ${!patient.abha_id ? '<div class="alert alert-warning small">Patient needs ABHA ID for linking</div>' : ""}
                        <button class="btn btn-sm btn-primary" onclick="selectPatient('${patient.patient_id}', '${patient.name}')">
                            <i class="fas fa-check"></i> Select Patient
                        </button>
                    </div>
                </div>
            `;
    } else {
      document.getElementById("searchResults").innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i> No patient found with this mobile number
                </div>
            `;
    }
  } catch (error) {
    utils.showError("Search failed: " + error.message);
  } finally {
    utils.hideLoading();
  }
}

// Select patient from search
function selectPatient(patientId, patientName) {
  document.getElementById("patientId").value = patientId;
  const modal = bootstrap.Modal.getInstance(
    document.getElementById("patientSearchModal"),
  );
  modal.hide();
  utils.showSuccess(`Selected patient: ${patientName}`);
}

// Apply filters
async function applyFilters() {
  const patientId = document.getElementById("filterPatientId").value;
  const contextType = document.getElementById("filterContextType").value;
  const linkingStatus = document.getElementById("filterLinkingStatus").value;

  // If patient ID is specified, fetch contexts for that patient
  if (patientId) {
    try {
      utils.showLoading();
      const careContexts = await api.careContexts.getByPatient(patientId);
      allCareContexts = careContexts;

      // Apply additional filters
      let filteredContexts = [...careContexts];

      if (contextType) {
        filteredContexts = filteredContexts.filter(
          (c) => c.context_type === contextType,
        );
      }

      if (linkingStatus) {
        filteredContexts = filteredContexts.filter(
          (c) =>
            c.linking_status?.toLowerCase() === linkingStatus.toLowerCase(),
        );
      }

      renderCareContextsTable(filteredContexts);
    } catch (error) {
      utils.showError("Failed to apply filters: " + error.message);
    } finally {
      utils.hideLoading();
    }
  } else {
    // Apply filters on current list
    let filteredContexts = [...allCareContexts];

    if (contextType) {
      filteredContexts = filteredContexts.filter(
        (c) => c.context_type === contextType,
      );
    }

    if (linkingStatus) {
      filteredContexts = filteredContexts.filter(
        (c) => c.linking_status?.toLowerCase() === linkingStatus.toLowerCase(),
      );
    }

    renderCareContextsTable(filteredContexts);
  }
}

// Clear filters
function clearFilters() {
  document.getElementById("filterPatientId").value = "";
  document.getElementById("filterContextType").value = "";
  document.getElementById("filterLinkingStatus").value = "";
  loadCareContexts();
}

// View care context details
async function viewCareContext(contextId) {
  try {
    utils.showLoading();

    // Find context in current list
    const context = allCareContexts.find(
      (c) => (c.context_id || c.id) === contextId,
    );

    if (!context) {
      utils.showError("Care context not found");
      return;
    }

    currentContext = context;

    // Populate modal
    document.getElementById("detailContextId").textContent =
      context.context_id || context.id;
    document.getElementById("detailLinkingStatus").textContent =
      context.linking_status || "unknown";
    document.getElementById("detailLinkingStatus").className =
      "badge " + getLinkingStatusClass(context.linking_status);
    document.getElementById("detailPatientId").textContent = context.patient_id;
    document.getElementById("detailPatientName").textContent =
      context.patient_name || "N/A";
    document.getElementById("detailContextName").textContent =
      context.context_name;
    document.getElementById("detailContextType").textContent =
      context.context_type || "N/A";
    document.getElementById("detailVisitId").textContent =
      context.visit_id || "N/A";
    document.getElementById("detailHipId").textContent =
      context.hip_id || "N/A";
    document.getElementById("detailDescription").textContent =
      context.description || "No description provided";
    document.getElementById("detailCreatedAt").textContent = utils.formatDate(
      context.created_at,
    );
    document.getElementById("detailUpdatedAt").textContent = utils.formatDate(
      context.updated_at,
    );

    // Show/hide linking error
    if (context.linking_status === "failed" && context.linking_error) {
      document.getElementById("linkingErrorSection").style.display = "block";
      document.getElementById("detailLinkingError").textContent =
        context.linking_error;
    } else {
      document.getElementById("linkingErrorSection").style.display = "none";
    }

    // Show modal
    const modal = new bootstrap.Modal(
      document.getElementById("contextDetailsModal"),
    );
    modal.show();
  } catch (error) {
    utils.showError("Failed to load care context details: " + error.message);
  } finally {
    utils.hideLoading();
  }
}

// Add health record for care context
function addHealthRecordForContext() {
  if (!currentContext) return;

  // Navigate to health records page with context info
  window.location.href = `health-records.html?patient_id=${currentContext.patient_id}&context_id=${currentContext.context_id || currentContext.id}`;
}

// Make functions globally accessible
window.viewCareContext = viewCareContext;
window.selectPatient = selectPatient;

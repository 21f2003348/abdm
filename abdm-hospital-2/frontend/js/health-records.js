// health-records.js - Health Records Management

let currentRecord = null;
let allHealthRecords = [];
let allVisits = [];
let selectedVisit = null;
let selectedCareContext = null;

// Initialize page
document.addEventListener("DOMContentLoaded", function () {
  // Set default date to today
  const today = new Date().toISOString().split("T")[0];
  document.getElementById("recordDate").value = today;

  // Load visits and health records
  loadActiveVisits();
  loadHealthRecords();

  // Event listeners
  document
    .getElementById("createHealthRecordForm")
    .addEventListener("submit", handleCreateHealthRecord);

  document
    .getElementById("visitSelect")
    .addEventListener("change", handleVisitSelection);

  document
    .getElementById("applyFiltersBtn")
    .addEventListener("click", applyFilters);
  document
    .getElementById("clearFiltersBtn")
    .addEventListener("click", clearFilters);

  // Check for URL params
  const urlParams = new URLSearchParams(window.location.search);
  const patientId = urlParams.get("patient_id");
  const visitId = urlParams.get("visit_id");
  const contextId = urlParams.get("context_id");

  if (visitId) {
    // Find and select the visit from loaded visits
    setTimeout(() => {
      const visitSelect = document.getElementById("visitSelect");
      const option = Array.from(visitSelect.options).find(
        (o) => o.value === visitId,
      );
      if (option) {
        visitSelect.value = visitId;
        handleVisitSelection();
      }
    }, 500);
  }

  if (patientId) {
    document.getElementById("filterPatientId").value = patientId;
  }

  if (contextId) {
    document.getElementById("contextId").value = contextId;
  }
});

// Load active visits for the dropdown
async function loadActiveVisits() {
  try {
    const visits = await api.visits.list();
    allVisits = visits.filter(
      (v) => v.status === "Scheduled" || v.status === "In Progress",
    );

    const visitSelect = document.getElementById("visitSelect");
    visitSelect.innerHTML = '<option value="">Select an active visit</option>';

    allVisits.forEach((visit) => {
      const option = document.createElement("option");
      option.value = visit.visitId || visit.id;
      const visitDate = new Date(
        visit.visitDate || visit.visit_date,
      ).toLocaleDateString();
      option.textContent = `${visit.patientName || "Unknown"} - ${visit.visitType || "Visit"} (${visitDate})`;
      visitSelect.appendChild(option);
    });
  } catch (error) {
    console.warn("Failed to load visits:", error.message);
    utils.showError("Could not load active visits");
  }
}

// Handle visit selection
async function handleVisitSelection() {
  const visitSelect = document.getElementById("visitSelect");
  const selectedVisitId = visitSelect.value;

  if (!selectedVisitId) {
    // Clear fields
    document.getElementById("patientId").value = "";
    document.getElementById("visitId").value = "";
    document.getElementById("contextId").value = "";
    document.getElementById("visitInfo").style.display = "none";
    selectedVisit = null;
    selectedCareContext = null;
    return;
  }

  // Find visit in allVisits
  selectedVisit = allVisits.find(
    (v) => (v.visitId || v.id) === selectedVisitId,
  );

  if (!selectedVisit) {
    utils.showError("Visit not found");
    return;
  }

  // Auto-fill fields
  document.getElementById("patientId").value =
    selectedVisit.patientId || selectedVisit.patient_id;
  document.getElementById("visitId").value = selectedVisitId;

  // Set doctor and department if available
  if (selectedVisit.doctorId || selectedVisit.doctor_id) {
    document.getElementById("doctorName").value =
      selectedVisit.doctorId || selectedVisit.doctor_id;
  }
  if (selectedVisit.department) {
    document.getElementById("department").value = selectedVisit.department;
  }

  // Set record date to visit date
  const visitDate = new Date(
    selectedVisit.visitDate || selectedVisit.visit_date,
  );
  document.getElementById("recordDate").value = visitDate
    .toISOString()
    .split("T")[0];

  // Show visit info
  const visitDate_display = new Date(
    selectedVisit.visitDate || selectedVisit.visit_date,
  ).toLocaleDateString();
  document.getElementById("visitPatientText").textContent =
    selectedVisit.patientName || "Unknown";
  document.getElementById("visitDetailsText").textContent =
    selectedVisit.visitType || "Visit";
  document.getElementById("visitMetaText").textContent =
    `${selectedVisit.department || "Department"} • ${visitDate_display}`;
  document.getElementById("visitInfo").style.display = "block";

  // Auto-generate and link care context
  await createAndLinkCareContext(
    selectedVisit.patientId || selectedVisit.patient_id,
    selectedVisit.department || "General",
    selectedVisit.visitType || "Visit",
  );
}

// Create and link care context to gateway
async function createAndLinkCareContext(patientId, department, visitType) {
  try {
    utils.showLoading();

    // Create care context via API
    const contextName = `${department} Care - ${new Date().getFullYear()}`;
    const response = await api.careContexts.createAndLink({
      patientId: patientId,
      contextName: contextName,
      description: `${visitType} visit care context`,
    });

    console.log("Care context API response:", response);

    if (response.localContext && response.localContext.contextId) {
      selectedCareContext = response.localContext.contextId;
      document.getElementById("contextId").value = selectedCareContext;
      utils.hideLoading();

      // Check if gateway linking succeeded
      if (
        response.gatewayResponse &&
        response.gatewayResponse.status === "pending"
      ) {
        utils.showInfo(
          `✅ Care context created locally (Gateway: ${response.gatewayResponse.message || "unavailable"})`,
        );
      } else {
        utils.showInfo("✅ Care context created and linked to ABDM Gateway");
      }
    } else {
      utils.hideLoading();
      console.warn("Care context response missing contextId:", response);
      utils.showError(
        "Could not create care context - will retry during record save",
      );
    }
  } catch (error) {
    utils.hideLoading();
    console.error("Error creating care context:", error);
    console.error("Full error details:", error.message, error.stack);
    // Don't block record creation if care context fails
    utils.showInfo(
      "⚠️ Care context creation failed: " +
        error.message +
        " - will retry when you save the record",
    );
  }
}

// Load all health records
async function loadHealthRecords() {
  try {
    utils.showLoading();

    const filterPatientId = document.getElementById("filterPatientId").value;

    let healthRecords = [];

    if (filterPatientId) {
      // Load records for specific patient
      console.log("Loading records for patient:", filterPatientId);
      healthRecords = await api.healthRecords.getByPatient(filterPatientId);
    } else {
      // Load records for all patients
      try {
        console.log("Loading all patients...");
        const patientsResponse = await api.patients.list();
        console.log("All patients:", patientsResponse);

        // Fetch records for each patient
        healthRecords = [];
        for (const patient of patientsResponse) {
          try {
            const patientRecords = await api.healthRecords.getByPatient(
              patient.patientId,
            );
            healthRecords = healthRecords.concat(patientRecords);
          } catch (error) {
            console.log(
              `Could not load records for patient ${patient.patientId}:`,
              error.message,
            );
          }
        }
        console.log("Loaded all health records:", healthRecords);
      } catch (error) {
        console.log("Could not load patients or their records:", error.message);
        healthRecords = [];
      }
    }

    // Ensure healthRecords is an array
    if (!Array.isArray(healthRecords)) {
      console.warn("API returned non-array response:", healthRecords);
      healthRecords = [];
    }

    allHealthRecords = healthRecords;
    renderHealthRecordsTable(healthRecords);
  } catch (error) {
    console.error("Failed to load health records:", error);
    utils.showError("Failed to load health records: " + error.message);

    const tbody = document.getElementById("healthRecordsTableBody");
    if (tbody) {
      tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-danger">
                    <i class="fas fa-exclamation-triangle"></i> Failed to load health records: ${error.message}
                </td>
            </tr>
        `;
    }
  } finally {
    utils.hideLoading();
  }
}

// Render health records table
function renderHealthRecordsTable(healthRecords) {
  const tbody = document.getElementById("healthRecordsTableBody");
  document.getElementById("recordCount").textContent = healthRecords.length;

  if (healthRecords.length === 0) {
    tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted">
                    <i class="fas fa-inbox"></i> No health records found. Create one above or filter by patient ID.
                </td>
            </tr>
        `;
    return;
  }

  tbody.innerHTML = healthRecords
    .map((record) => {
      // Handle both old and new API response formats
      // New format: type, date, receivedAt
      // Old format: record_type, record_date, created_at
      const recordType = record.type || record.record_type || "N/A";
      const recordDate = record.date || record.record_date;
      const formattedDate = recordDate ? utils.formatDate(recordDate) : "N/A";

      const recordId = record.id || record.record_id;
      const patientName =
        record.patientName || record.patient_name || "Unknown";
      const patientId = record.patientId || record.patient_id || "Unknown";
      const title = record.title || recordType || "Record";

      // Extract doctor name from data if available
      let doctorName = "N/A";
      if (record.data) {
        if (typeof record.data === "string") {
          try {
            const dataObj = JSON.parse(record.data);
            doctorName =
              dataObj.doctorName ||
              dataObj.performedBy ||
              dataObj.prescribedBy ||
              dataObj.doctor_name ||
              "N/A";
          } catch (e) {
            doctorName = "N/A";
          }
        } else {
          doctorName =
            record.data.doctorName ||
            record.data.performedBy ||
            record.data.prescribedBy ||
            record.data.doctor_name ||
            "N/A";
        }
      }

      return `
            <tr>
                <td><small>${recordId}</small></td>
                <td>
                    <div>${patientName}</div>
                    <small class="text-muted">${patientId}</small>
                </td>
                <td>${title}</td>
                <td><span class="badge bg-info">${recordType}</span></td>
                <td>${formattedDate}</td>
                <td>${doctorName}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="viewHealthRecord('${recordId}')">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            </tr>
        `;
    })
    .join("");
}

// Handle create health record form submission
async function handleCreateHealthRecord(e) {
  e.preventDefault();

  // Validation
  const visitId = document.getElementById("visitSelect").value;
  const patientId = document.getElementById("patientId").value.trim();
  const recordType = document.getElementById("recordType").value;
  const recordDate = document.getElementById("recordDate").value;
  const title = document.getElementById("title").value.trim();

  if (!visitId) {
    utils.showError("Please select a visit first");
    return;
  }

  if (!patientId || !recordType || !recordDate || !title) {
    utils.showError("Please fill in all required fields");
    return;
  }

  try {
    utils.showLoading();

    // Prepare health record data
    const recordData = {
      patientId,
      recordType,
      recordDate,
      title,
      data: {
        title: title,
        recordType: recordType,
        doctorName:
          document.getElementById("doctorName").value.trim() || "Not specified",
        department:
          document.getElementById("department").value.trim() || "General",
        visitId: document.getElementById("visitId").value || visitId,
        contentText: document.getElementById("content").value.trim() || null,
        fileUrl: document.getElementById("fileUrl").value.trim() || null,
      },
      dataText: document.getElementById("content").value.trim() || null,
    };

    // Step 1: Create health record in database
    const createResponse = await api.healthRecords.create(recordData);
    console.log("Health record created:", createResponse);

    // Step 2: Create care context if not already created
    if (!selectedCareContext && selectedVisit) {
      await createAndLinkCareContext(
        patientId,
        document.getElementById("department").value || "General",
        recordType,
      );
    }

    // Step 3: Notify gateway about the new record
    try {
      const notifyResponse = await api.healthRecords.notifyGateway(
        patientId,
        createResponse.id,
      );
      console.log("Gateway notified:", notifyResponse);
      utils.showSuccess(
        "✅ Health record created, linked to care context, and registered with ABDM Gateway!",
      );
    } catch (notifyError) {
      console.warn("Gateway notification failed:", notifyError.message);
      utils.showSuccess(
        "✅ Health record created and linked to care context (gateway notification pending)",
      );
    }

    e.target.reset();
    document.getElementById("recordDate").value = new Date()
      .toISOString()
      .split("T")[0];

    // Reset visit selection
    document.getElementById("visitSelect").value = "";
    document.getElementById("patientId").value = "";
    document.getElementById("visitId").value = "";
    document.getElementById("contextId").value = "";
    document.getElementById("visitInfo").style.display = "none";
    selectedVisit = null;
    selectedCareContext = null;

    await loadHealthRecords();
  } catch (error) {
    utils.showError("Failed to create health record: " + error.message);
  } finally {
    utils.hideLoading();
  }
}

// Apply filters
async function applyFilters() {
  const patientId = document.getElementById("filterPatientId").value;
  const recordType = document.getElementById("filterRecordType").value;
  const startDate = document.getElementById("filterStartDate").value;
  const endDate = document.getElementById("filterEndDate").value;

  // If patient ID is specified, fetch records for that patient
  if (patientId) {
    try {
      utils.showLoading();
      const healthRecords = await api.healthRecords.getByPatient(patientId);
      allHealthRecords = healthRecords;

      // Apply additional filters
      let filteredRecords = [...healthRecords];

      if (recordType) {
        filteredRecords = filteredRecords.filter(
          (r) => (r.type || r.record_type) === recordType,
        );
      }

      if (startDate) {
        const recordDateField = (r) => r.date || r.record_date;
        filteredRecords = filteredRecords.filter(
          (r) => recordDateField(r) >= startDate,
        );
      }

      if (endDate) {
        const recordDateField = (r) => r.date || r.record_date;
        filteredRecords = filteredRecords.filter(
          (r) => recordDateField(r) <= endDate,
        );
      }

      renderHealthRecordsTable(filteredRecords);
    } catch (error) {
      utils.showError("Failed to apply filters: " + error.message);
    } finally {
      utils.hideLoading();
    }
  } else {
    // Apply filters on current list
    let filteredRecords = [...allHealthRecords];

    if (recordType) {
      filteredRecords = filteredRecords.filter(
        (r) => (r.type || r.record_type) === recordType,
      );
    }

    if (startDate) {
      const recordDateField = (r) => r.date || r.record_date;
      filteredRecords = filteredRecords.filter(
        (r) => recordDateField(r) >= startDate,
      );
    }

    if (endDate) {
      const recordDateField = (r) => r.date || r.record_date;
      filteredRecords = filteredRecords.filter(
        (r) => recordDateField(r) <= endDate,
      );
    }

    renderHealthRecordsTable(filteredRecords);
  }
}

// Clear filters
function clearFilters() {
  document.getElementById("filterPatientId").value = "";
  document.getElementById("filterRecordType").value = "";
  document.getElementById("filterStartDate").value = "";
  document.getElementById("filterEndDate").value = "";
  loadHealthRecords();
}

// View health record details
async function viewHealthRecord(recordId) {
  try {
    utils.showLoading();

    // Find record in current list
    const record = allHealthRecords.find(
      (r) => (r.record_id || r.id) === recordId,
    );

    if (!record) {
      utils.showError("Health record not found");
      return;
    }

    currentRecord = record;

    // Handle both API response formats
    const recordType = record.type || record.record_type || "N/A";
    const recordDate = record.date || record.record_date;
    const formattedRecordDate = recordDate
      ? utils.formatDate(recordDate)
      : "N/A";
    const formattedCreatedAt =
      record.receivedAt || record.created_at
        ? utils.formatDate(record.receivedAt || record.created_at)
        : "N/A";
    const formattedUpdatedAt = record.updated_at
      ? utils.formatDate(record.updated_at)
      : "N/A";

    let doctorName = "N/A";
    let department = "N/A";
    let contentText = "No content provided";

    // Extract data from record.data
    if (record.data) {
      if (typeof record.data === "string") {
        try {
          const dataObj = JSON.parse(record.data);
          doctorName =
            dataObj.doctorName ||
            dataObj.performedBy ||
            dataObj.prescribedBy ||
            dataObj.doctor_name ||
            "N/A";
          department = dataObj.department || "N/A";
          contentText =
            dataObj.contentText || dataObj.content || "No content provided";
        } catch (e) {
          contentText = record.data;
        }
      } else {
        doctorName =
          record.data.doctorName ||
          record.data.performedBy ||
          record.data.prescribedBy ||
          record.data.doctor_name ||
          "N/A";
        department = record.data.department || "N/A";
        contentText =
          record.data.contentText ||
          record.data.content ||
          "No content provided";
      }
    }

    // Populate modal
    document.getElementById("detailRecordId").textContent =
      record.id || record.record_id;
    document.getElementById("detailRecordType").textContent = recordType;
    document.getElementById("detailPatientId").textContent =
      record.patientId || record.patient_id || "N/A";
    document.getElementById("detailPatientName").textContent =
      record.patientName || record.patient_name || "N/A";
    document.getElementById("detailVisitId").textContent =
      record.visitId || record.visit_id || "N/A";
    document.getElementById("detailContextId").textContent =
      record.contextId || record.context_id || "N/A";
    document.getElementById("detailRecordDate").textContent =
      formattedRecordDate;
    document.getElementById("detailTitle").textContent =
      record.title || recordType || "Record";
    document.getElementById("detailDoctorName").textContent = doctorName;
    document.getElementById("detailDepartment").textContent = department;
    document.getElementById("detailContent").textContent = contentText;
    document.getElementById("detailCreatedAt").textContent = formattedCreatedAt;
    document.getElementById("detailUpdatedAt").textContent = formattedUpdatedAt;

    // Show/hide file URL
    if (record.fileUrl || (record.data && record.data.fileUrl)) {
      document.getElementById("fileUrlSection").style.display = "block";
      const fileUrl = record.fileUrl || record.data.fileUrl;
      document.getElementById("detailFileUrl").href = fileUrl;
    } else {
      document.getElementById("fileUrlSection").style.display = "none";
    }

    // Show modal
    const modal = new bootstrap.Modal(
      document.getElementById("recordDetailsModal"),
    );
    modal.show();
  } catch (error) {
    utils.showError("Failed to load health record details: " + error.message);
  } finally {
    utils.hideLoading();
  }
}

// Make functions globally accessible
window.viewHealthRecord = viewHealthRecord;

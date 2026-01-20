// health-records.js - Health Records Management

let currentRecord = null;
let allHealthRecords = [];

// Initialize page
document.addEventListener("DOMContentLoaded", function () {
  // Set default date to today
  const today = new Date().toISOString().split("T")[0];
  document.getElementById("recordDate").value = today;

  // Load health records
  loadHealthRecords();

  // Load active visits for dropdown
  loadActiveVisitsDropdown();

  // Event listeners
  document
    .getElementById("createHealthRecordForm")
    .addEventListener("submit", handleCreateHealthRecord);

  const visitDropdown = document.getElementById("visitDropdown");
  if (visitDropdown) {
    visitDropdown.addEventListener("change", handleVisitSelection);
  }

  const searchPatientBtn = document.getElementById("searchPatientBtn");
  if (searchPatientBtn) {
    searchPatientBtn.addEventListener("click", handleSearchPatient);
  }

  document
    .getElementById("applyFiltersBtn")
    .addEventListener("click", applyFilters);
  document
    .getElementById("clearFiltersBtn")
    .addEventListener("click", clearFilters);

  // Check for URL params (legacy support)
  const urlParams = new URLSearchParams(window.location.search);
  const visitId = urlParams.get("visit_id");
  if (visitId) {
    // Try to select visit from dropdown if it exists
    setTimeout(() => {
      const dropdown = document.getElementById("visitDropdown");
      if (dropdown) {
        const option = Array.from(dropdown.options).find(
          (opt) => opt.dataset.visitId === visitId,
        );
        if (option) {
          dropdown.value = option.value;
          handleVisitSelection({ target: dropdown });
        }
      }
    }, 500);
  }
});

// Load active visits and populate dropdown
async function loadActiveVisitsDropdown() {
  const dropdown = document.getElementById("visitDropdown");
  const statusElement = document.getElementById("visitDropdownStatus");

  if (!dropdown) {
    console.error("Visit dropdown element not found!");
    return;
  }

  dropdown.innerHTML = '<option value="">-- Select Visit --</option>';
  dropdown.disabled = true;

  if (statusElement) {
    statusElement.textContent = "Loading active visits...";
    statusElement.className = "text-muted small";
  }

  try {
    const visits = await api.visits.getActive();
    console.log("[DEBUG] Active visits fetched:", visits);

    if (!Array.isArray(visits)) {
      throw new Error("/api/visit/active did not return an array.");
    }

    if (visits.length === 0) {
      dropdown.innerHTML =
        '<option value="">No active visits available</option>';
      dropdown.disabled = true;
      if (statusElement) {
        statusElement.textContent = "No active visits available.";
        statusElement.className = "text-muted small";
      }
      return;
    }

    visits.forEach((visit) => {
      const option = document.createElement("option");
      option.value = visit.visitId;
      // Show patient name, visit type, department, and date
      let displayText = `${visit.patientName || "Unknown"} - ${visit.visitType} (${visit.department})`;
      if (visit.visitDate) {
        const date = new Date(visit.visitDate);
        displayText += ` - ${date.toLocaleDateString()}`;
      }
      option.textContent = displayText;
      option.dataset.visit = JSON.stringify(visit);
      dropdown.appendChild(option);
    });

    dropdown.disabled = false;
    if (statusElement) {
      statusElement.textContent = `Loaded ${visits.length} active visit(s).`;
      statusElement.className = "text-success small";
    }
    console.log(
      `[DEBUG] Dropdown populated with ${visits.length} active visits`,
    );
  } catch (error) {
    console.error("Error loading active visits dropdown:", error);
    dropdown.innerHTML = '<option value="">Error loading visits</option>';
    dropdown.disabled = true;
    if (statusElement) {
      statusElement.textContent = `Error: ${error.message}`;
      statusElement.className = "text-danger small";
    }
    utils.showError("Failed to load active visits: " + error.message);
  }
}

// Handle visit selection from dropdown
function handleVisitSelection(e) {
  const dropdown = e.target || document.getElementById("visitDropdown");
  const selectedOption = dropdown.options[dropdown.selectedIndex];

  if (selectedOption.value) {
    try {
      const visit = JSON.parse(selectedOption.dataset.visit);

      // Auto-fill hidden fields
      document.getElementById("patientId").value = visit.patientId;
      document.getElementById("visitId").value = visit.visitId;
      document.getElementById("doctorName").value = visit.doctorId || "";
      document.getElementById("department").value = visit.department || "";

      // Auto-fill visible fields
      document.getElementById("recordDate").value = visit.visitDate
        ? visit.visitDate.split("T")[0]
        : new Date().toISOString().split("T")[0];

      // Show visit details
      document.getElementById("selectedPatientName").textContent =
        visit.patientName || "Unknown";
      document.getElementById("selectedVisitType").textContent =
        visit.visitType || "-";
      document.getElementById("selectedDepartment").textContent =
        visit.department || "-";
      document.getElementById("selectedDoctor").textContent =
        visit.doctorId || "-";
      document.getElementById("visitDetailsDiv").style.display = "block";

      utils.showSuccess("Visit selected! Fields auto-filled.");
    } catch (error) {
      console.error("Error parsing visit data:", error);
      utils.showError("Error selecting visit");
    }
  } else {
    // Clear fields if no visit selected
    document.getElementById("patientId").value = "";
    document.getElementById("visitId").value = "";
    document.getElementById("doctorName").value = "";
    document.getElementById("department").value = "";
    document.getElementById("visitDetailsDiv").style.display = "none";
  }
}

// Load all health records
async function loadHealthRecords() {
  try {
    utils.showLoading();

    // Try to get health records from API
    const filterPatientId = document.getElementById("filterPatientId").value;

    let healthRecords = [];
    if (filterPatientId) {
      healthRecords = await api.healthRecords.getByPatient(filterPatientId);
    } else {
      // Try to get all records
      try {
        healthRecords = await api.healthRecords.list();
      } catch (error) {
        console.log("List endpoint not available, showing empty list");
        healthRecords = [];
      }
    }

    allHealthRecords = healthRecords;
    renderHealthRecordsTable(healthRecords);
  } catch (error) {
    utils.showError("Failed to load health records: " + error.message);
    document.getElementById("healthRecordsTableBody").innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-danger">
                    <i class="fas fa-exclamation-triangle"></i> Failed to load health records
                </td>
            </tr>
        `;
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
      // Handle both ISO and formatted dates
      const recordDate = record.date
        ? utils.formatDate(record.date)
        : utils.formatDate(record.receivedAt);
      const recordId = record.id || record.record_id;
      const patientName = record.patientName || "Unknown";
      const patientId = record.patientId || "Unknown";
      const title = record.title || record.type || "Record";
      const recordType = record.type || "N/A";

      // Extract doctor name from data if available
      const doctorName =
        (record.data &&
          (record.data.performedBy ||
            record.data.prescribedBy ||
            record.data.doctor_name)) ||
        "N/A";

      return `
            <tr>
                <td><small>${recordId}</small></td>
                <td>
                    <div>${patientName}</div>
                    <small class="text-muted">${patientId}</small>
                </td>
                <td>${title}</td>
                <td><span class="badge bg-info">${recordType}</span></td>
                <td>${recordDate}</td>
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
  const visitId = document.getElementById("visitId").value.trim();
  const patientId = document.getElementById("patientId").value.trim();
  const recordType = document.getElementById("recordType").value;
  const recordDate = document.getElementById("recordDate").value;
  const title = document.getElementById("title").value.trim();

  if (!visitId || !patientId || !recordType || !recordDate || !title) {
    utils.showError("Please select a visit and fill in all required fields");
    return;
  }

  try {
    utils.showLoading();

    const doctorName = document.getElementById("doctorName").value.trim();
    const department = document.getElementById("department").value.trim();
    const content = document.getElementById("content").value.trim();
    const fileUrl = document.getElementById("fileUrl").value.trim();

    // Simplified payload - care context and linking request will be auto-generated
    const payload = {
      patientId,
      recordType,
      recordDate,
      title,
      content: content || null,
      doctorName: doctorName || null,
      department: department || null,
      fileUrl: fileUrl || null,
      data: {
        title,
        content: content || null,
        doctorName: doctorName || null,
        department: department || null,
        fileUrl: fileUrl || null,
        visitId: visitId,
      },
      dataText: content || null,
    };

    await api.healthRecords.create(payload);

    utils.showSuccess(
      "Health record created successfully! Care context and linking request are being generated.",
    );
    e.target.reset();
    document.getElementById("recordDate").value = new Date()
      .toISOString()
      .split("T")[0];
    document.getElementById("visitDetailsDiv").style.display = "none";

    // Reload dropdown to refresh active visits
    await loadActiveVisitsDropdown();
    await loadHealthRecords();
  } catch (error) {
    utils.showError("Failed to create health record: " + error.message);
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
                            <strong>Mobile:</strong> ${patient.mobile_number}
                        </p>
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
          (r) => r.record_type === recordType,
        );
      }

      if (startDate) {
        filteredRecords = filteredRecords.filter(
          (r) => r.record_date >= startDate,
        );
      }

      if (endDate) {
        filteredRecords = filteredRecords.filter(
          (r) => r.record_date <= endDate,
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
        (r) => r.record_type === recordType,
      );
    }

    if (startDate) {
      filteredRecords = filteredRecords.filter(
        (r) => r.record_date >= startDate,
      );
    }

    if (endDate) {
      filteredRecords = filteredRecords.filter((r) => r.record_date <= endDate);
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
    console.log("[DEBUG] viewHealthRecord called with recordId:", recordId);
    console.log("[DEBUG] allHealthRecords length:", allHealthRecords.length);

    // Find record in current list - handle both id and record_id
    const record = allHealthRecords.find(
      (r) => (r.id || r.record_id) === recordId,
    );

    if (!record) {
      console.error("[DEBUG] Record not found. Available IDs:", allHealthRecords.map(r => r.id || r.record_id));
      utils.showError("Health record not found");
      utils.hideLoading();
      return;
    }

    console.log("[DEBUG] Found record:", record);
    currentRecord = record;

    // Extract data from data_json/data field if needed
    const data = record.data || {};
    
    // Helper function to safely set text content
    const setTextContent = (elementId, value) => {
      const element = document.getElementById(elementId);
      if (element) {
        element.textContent = value;
      } else {
        console.warn(`[DEBUG] Element ${elementId} not found`);
      }
    };
    
    // Populate modal - handle both camelCase and snake_case field names
    const recordIdValue = record.id || record.record_id || "N/A";
    setTextContent("detailRecordId", recordIdValue);
    
    const recordType = record.type || record.record_type || "N/A";
    setTextContent("detailRecordType", recordType);
    
    const patientId = record.patientId || record.patient_id || "N/A";
    setTextContent("detailPatientId", patientId);
    
    const patientName = record.patientName || record.patient_name || "N/A";
    setTextContent("detailPatientName", patientName);
    
    // Visit ID - check data_json first, then top-level
    const visitId = record.visitId || record.visit_id || data.visitId || data.visit_id || "N/A";
    setTextContent("detailVisitId", visitId);
    
    // Care Context ID
    const contextId = record.careContextId || record.care_context_id || record.contextId || record.context_id || "N/A";
    setTextContent("detailContextId", contextId);
    
    const recordDate = record.date || record.record_date;
    setTextContent("detailRecordDate", utils.formatDate(recordDate) || "N/A");
    
    // Title - check data_json first, then top-level
    const title = record.title || data.title || record.type || "N/A";
    setTextContent("detailTitle", title);
    
    // Doctor Name - check data_json first (doctorName or doctor_name), then top-level
    const doctorName = record.doctor_name || data.doctorName || data.doctor_name || "N/A";
    setTextContent("detailDoctorName", doctorName);
    
    // Department - check data_json first, then top-level
    const department = record.department || data.department || "N/A";
    setTextContent("detailDepartment", department);
    
    // Content - check data_json first, then top-level, then dataText
    const content = record.content || data.content || record.dataText || record.data_text || "No content provided";
    setTextContent("detailContent", content);
    
    const createdAt = record.created_at;
    setTextContent("detailCreatedAt", utils.formatDate(createdAt) || "N/A");
    
    const updatedAt = record.updated_at;
    setTextContent("detailUpdatedAt", utils.formatDate(updatedAt) || "N/A");

    // Show/hide file URL - check data_json first, then top-level
    const fileUrl = record.fileUrl || record.file_url || data.fileUrl || data.file_url;
    const fileUrlSection = document.getElementById("fileUrlSection");
    const detailFileUrl = document.getElementById("detailFileUrl");
    if (fileUrl && fileUrlSection && detailFileUrl) {
      fileUrlSection.style.display = "block";
      detailFileUrl.href = fileUrl;
    } else if (fileUrlSection) {
      fileUrlSection.style.display = "none";
    }

    console.log("[DEBUG] Modal populated, showing modal...");
    // Show modal
    const modalElement = document.getElementById("recordDetailsModal");
    if (!modalElement) {
      console.error("[DEBUG] Modal element not found!");
      utils.showError("Modal element not found");
      utils.hideLoading();
      return;
    }
    
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
    console.log("[DEBUG] Modal shown");
  } catch (error) {
    console.error("[DEBUG] Error in viewHealthRecord:", error);
    utils.showError("Failed to load health record details: " + error.message);
  } finally {
    utils.hideLoading();
  }
}

// Make functions globally accessible
window.viewHealthRecord = viewHealthRecord;
window.selectPatient = selectPatient;

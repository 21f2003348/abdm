// patient-history.js - view patient visits and health records

let selectedPatient = null;
let visitsCache = [];
let recordsCache = [];
let allPatients = [];
let pollInterval = null;

function setLoading(isLoading) {
  const btn = document.getElementById("loadHistoryBtn");
  if (btn) btn.disabled = isLoading || !selectedPatient;
}

// Load all patients into dropdown on page load
async function loadPatientsDropdown() {
  try {
    console.log("Loading patients list from API...");
    allPatients = await api.patients.list();
    console.log("Patients loaded:", allPatients);

    const dropdown = document.getElementById("patientDropdown");
    if (!dropdown) {
      console.error("Dropdown element not found!");
      return;
    }

    dropdown.innerHTML = '<option value="">-- Select Patient --</option>';

    if (!allPatients || allPatients.length === 0) {
      console.warn("No patients returned from API");
      dropdown.innerHTML += "<option disabled>No patients found</option>";
      return;
    }

    allPatients.forEach((patient) => {
      const option = document.createElement("option");
      const patientId = patient.patientId || patient.id;
      const patientName = patient.name || "Unknown";
      const patientMobile = patient.mobile || patient.mobileNumber || "N/A";
      const patientAbha = patient.abhaId ? ` (${patient.abhaId})` : "";

      option.value = patientId;
      option.textContent = `${patientName} - ${patientMobile}${patientAbha}`;
      option.dataset.patientData = JSON.stringify(patient);
      dropdown.appendChild(option);
      console.log("Added patient option:", patientName);
    });

    console.log("Dropdown populated with " + allPatients.length + " patients");
  } catch (err) {
    console.error("Failed to load patients:", err);
    const dropdown = document.getElementById("patientDropdown");
    if (dropdown) {
      dropdown.innerHTML +=
        '<option disabled style="color: red;">Error loading patients</option>';
    }
    utils.showError("Failed to load patient list: " + err.message);
  }
}

// Show selected patient summary
function showPatientSummary(patient) {
  selectedPatient = patient;
  document.getElementById("pName").textContent = patient.name || "";
  document.getElementById("pMobile").textContent =
    patient.mobile || patient.mobileNumber || "";
  document.getElementById("pAbha").textContent = patient.abhaId || "Not linked";
  document.getElementById("pId").textContent = patient.patientId || patient.id;
  document.getElementById("patientSummary").classList.remove("d-none");
  document.getElementById("searchNotFound").classList.add("d-none");
  document.getElementById("loadHistoryBtn").disabled = false;
}

// Search patient by ABHA ID
async function searchByAbha() {
  const abhaValue = document.getElementById("abhaSearchValue").value.trim();
  if (!abhaValue) {
    utils.showError("Enter ABHA ID to search");
    return;
  }

  try {
    utils.showLoading();
    const patients = await api.patients.list();
    const found = patients.find(
      (p) => (p.abhaId || "").toLowerCase() === abhaValue.toLowerCase(),
    );

    if (!found) {
      // Patient not found
      document.getElementById("patientSummary").classList.add("d-none");
      document.getElementById("searchNotFound").classList.remove("d-none");
      document.getElementById("loadHistoryBtn").disabled = true;
      selectedPatient = null;
      utils.showError("Patient not registered yet");
      return;
    }

    // Patient found
    showPatientSummary(found);

    // Update dropdown to reflect selection
    const dropdown = document.getElementById("patientDropdown");
    dropdown.value = found.patientId || found.id;

    utils.showSuccess("Patient found!");
  } catch (err) {
    utils.showError("Search failed: " + err.message);
  } finally {
    utils.hideLoading();
  }
}

function renderVisits(visits) {
  const body = document.getElementById("visitsBody");
  if (!body) return;
  if (!visits || visits.length === 0) {
    body.innerHTML = `
      <tr>
        <td colspan="4" class="text-center text-muted">
          <i class="fas fa-inbox"></i> No visits found
        </td>
      </tr>`;
    return;
  }
  body.innerHTML = visits
    .map((v) => {
      const date = utils.formatDate(v.visitDate || v.visit_date);
      const status = v.status || "";
      const statusClass =
        status === "Completed"
          ? "bg-success"
          : status === "In Progress"
            ? "bg-warning"
            : status === "Cancelled"
              ? "bg-secondary"
              : "bg-primary";
      return `
        <tr>
          <td>${date || "-"}</td>
          <td>${v.visitType || v.visit_type || "-"}</td>
          <td>${v.department || "-"}</td>
          <td><span class="badge ${statusClass}">${status || "Unknown"}</span></td>
        </tr>`;
    })
    .join("");
}

function renderRecords(records) {
  const localBody = document.getElementById("localRecordsBody");
  const externalBody = document.getElementById("externalRecordsBody");

  // Separate records
  const localRecords = records.filter(r => !r.sourceHospital);
  const externalRecords = records.filter(r => r.sourceHospital);

  // Render Local
  if (localBody) {
    if (localRecords.length === 0) {
      localBody.innerHTML = `
        <tr>
          <td colspan="4" class="text-center text-muted">
            <i class="fas fa-inbox"></i> No local records
          </td>
        </tr>`;
    } else {
      localBody.innerHTML = localRecords.map(r => {
        const date = utils.formatDate(r.record_date || r.recordDate);
        const type = r.record_type || r.recordType || "Unknown";
        // Local records usually don't have sourceHospital set, or it's null
        return `
          <tr>
            <td>${date || "-"}</td>
            <td>${type}</td>
            <td>Local</td>
            <td>
              <button class="btn btn-sm btn-outline-primary" onclick='alert("View functionality not implemented in demo")'>
                <i class="fas fa-eye"></i>
              </button>
            </td>
          </tr>`;
      }).join("");
    }
  }

  // Render External
  if (externalBody) {
    if (externalRecords.length === 0) {
      externalBody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center text-muted">
            <i class="fas fa-network-wired"></i> No external records fetched yet
          </td>
        </tr>`;
    } else {
      externalBody.innerHTML = externalRecords.map((r, index) => {
        const date = utils.formatDate(r.record_date || r.recordDate || r.date);
        const type = r.record_type || r.recordType || r.type || "Unknown";
        const source = r.source_hospital || r.sourceHospital || "External";
        
        // Format source hospital name (remove bridge prefix, make readable)
        const formattedSource = source
          .replace(/^BRIDGE[-_]?/i, "")
          .replace(/[-_]/g, " ")
          .replace(/\b\w/g, l => l.toUpperCase());
        
        // Extract structured data from data_json
        const data = r.data || {};
        const title = data.title || data.testName || data.reportType || type;
        const content = data.content || data.notes || data.description || "";
        const doctorName = data.doctorName || data.doctor_name || data.prescribedBy || data.performedBy || "N/A";
        const department = data.department || "N/A";
        
        // Create formatted preview
        let dataPreview = "";
        if (title && title !== type) {
          dataPreview = `<strong>${title}</strong>`;
          if (doctorName && doctorName !== "N/A") {
            dataPreview += `<br><small class="text-muted"><i class="fas fa-user-md"></i> ${doctorName}</small>`;
          }
          if (department && department !== "N/A") {
            dataPreview += `<br><small class="text-muted"><i class="fas fa-building"></i> ${department}</small>`;
          }
          if (content) {
            const contentPreview = content.length > 50 ? content.substring(0, 50) + "..." : content;
            dataPreview += `<br><small class="text-muted">${contentPreview}</small>`;
          }
        } else {
          dataPreview = `<small class="text-muted">${type} record from ${formattedSource}</small>`;
        }

        // Create unique ID for modal
        const modalId = `externalRecordModal${index}`;
        const recordId = r.id || r.record_id || `external-${index}`;

        return `
          <tr>
            <td>${date || "-"}</td>
            <td><span class="badge bg-info">${type}</span></td>
            <td><span class="badge bg-warning text-dark"><i class="fas fa-hospital"></i> ${formattedSource}</span></td>
            <td><div class="small">${dataPreview}</div></td>
            <td>
              <button class="btn btn-sm btn-outline-primary view-external-record-btn" data-record-index="${index}">
                <i class="fas fa-eye"></i> View
              </button>
            </td>
          </tr>`;
      }).join("");
    }
  }
}

async function searchPatient() {
  // Deprecated - use searchByAbha or dropdown instead
  searchByAbha();
}

async function loadHistory() {
  if (!selectedPatient) {
    utils.showError("Select a patient first");
    return;
  }

  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }

  try {
    setLoading(true);
    utils.showInfo("Requesting visits and records...");

    // Trigger Consent/Data Fetch if ABHA ID is present
    if (selectedPatient.abhaId) {
      try {
        // Determine target HIP based on current port (Simple Demo Logic)
        // 8080 (Hospital 1) -> Requests from HOSPITAL-2
        // 8081 (Hospital 2) -> Requests from HOSPITAL-1
        const currentPort = window.location.port;
        const targetHip = currentPort === "8081" ? "HOSPITAL-1" : "HOSPITAL-2"; // Default to HOSP-2 if 8080

        console.log(`[Automatic] Initiating consent request to ${targetHip} for ${selectedPatient.abhaId}`);
        utils.showInfo(`Initiating data fetch from ${targetHip}...`);

        const consentRes = await api.consent.init({
          patientId: selectedPatient.abhaId,
          hipId: targetHip,
          purpose: { code: "CAREMGT", text: "Patient History Check" }
        });
        console.log("Consent initiated:", consentRes);
        utils.showSuccess("Data fetch initiated via Gateway. Waiting for data...");

        // Wait a few seconds for Mock Gateway to process/webhook to fire
        // In a real app, we would poll or wait for a user notification
        await new Promise(r => setTimeout(r, 2000));
      } catch (e) {
        console.warn("Consent init failed (maybe already active or offline):", e);
        // Don't block local load
      }
    }

    // Load visits (local)
    const visitsRes = await api.visits.getByPatient(
      selectedPatient.patientId || selectedPatient.id,
    );
    visitsCache = visitsRes.visits || visitsRes || [];
    renderVisits(visitsCache);

    // Load health records (local + external if backend merged)
    const fetchAndRenderRecords = async () => {
      const records = await api.healthRecords.getByPatient(selectedPatient.patientId || selectedPatient.id);
      recordsCache = records || [];
      renderRecords(recordsCache);
      return records || [];
    };

    await fetchAndRenderRecords();

    // Start Polling Method if we suspect external data might be coming
    // (We assume consent was triggered if we reached here without error, or we just poll anyway to be safe)
    const loader = document.getElementById("externalLoader");
    if (loader) loader.classList.remove("d-none");

    let attempts = 0;
    const maxAttempts = 10; // 30 seconds total

    pollInterval = setInterval(async () => {
      attempts++;
      console.log(`Polling for external data (Attempt ${attempts}/${maxAttempts})...`);

      const freshRecords = await fetchAndRenderRecords();
      const externalCount = freshRecords.filter(r => r.sourceHospital).length;

      if (externalCount > 0) {
        utils.showSuccess(`Received ${externalCount} external records!`);
        clearInterval(pollInterval);
        if (loader) loader.classList.add("d-none");
        pollInterval = null;
      } else if (attempts >= maxAttempts) {
        console.log("Polling timed out.");
        clearInterval(pollInterval);
        if (loader) loader.classList.add("d-none");
        pollInterval = null;
      }
    }, 3000);

    document.getElementById("historyStatus").innerHTML =
      '<div class="alert alert-info mb-0">History loaded. Checking for external records...</div>';
  } catch (err) {
    document.getElementById("historyStatus").innerHTML =
      `<div class="alert alert-danger mb-0">Failed to load history: ${err.message}</div>`;
  } finally {
    setLoading(false);
  }
}

// View external record details
function viewExternalRecord(record) {
  try {
    // Handle both direct object and JSON string
    if (typeof record === 'string') {
      record = JSON.parse(record);
    }
    const data = record.data || {};
    
    // Format source hospital name
    const source = record.source_hospital || record.sourceHospital || "External";
    const formattedSource = source
      .replace(/^BRIDGE[-_]?/i, "")
      .replace(/[-_]/g, " ")
      .replace(/\b\w/g, l => l.toUpperCase());
    
    // Extract and format fields
    const date = utils.formatDate(record.record_date || record.recordDate || record.date);
    const type = record.record_type || record.recordType || record.type || "Unknown";
    const title = data.title || data.testName || data.reportType || type;
    const content = data.content || data.notes || data.description || data.summary || "";
    const doctorName = data.doctorName || data.doctor_name || data.prescribedBy || data.performedBy || "N/A";
    const department = data.department || "N/A";
    const medicines = data.medicines || data.medications || [];
    const testResults = data.testResults || data.results || [];
    const diagnosis = data.diagnosis || data.condition || "";
    
    // Build formatted HTML
    let contentHtml = `
      <div class="row mb-3">
        <div class="col-md-6">
          <strong>Record Type:</strong>
          <span class="badge bg-info ms-2">${type}</span>
        </div>
        <div class="col-md-6">
          <strong>Date:</strong> ${date || "N/A"}
        </div>
      </div>
      <div class="row mb-3">
        <div class="col-md-6">
          <strong>Source Hospital:</strong>
          <span class="badge bg-warning text-dark ms-2">
            <i class="fas fa-hospital"></i> ${formattedSource}
          </span>
        </div>
        <div class="col-md-6">
          <strong>Request ID:</strong>
          <small class="text-muted">${record.requestId || record.request_id || "N/A"}</small>
        </div>
      </div>
      <hr>
      <div class="row mb-3">
        <div class="col-12">
          <h6 class="text-primary">${title}</h6>
        </div>
      </div>`;
    
    if (doctorName && doctorName !== "N/A") {
      contentHtml += `
        <div class="row mb-2">
          <div class="col-md-6">
            <strong><i class="fas fa-user-md"></i> Doctor:</strong> ${doctorName}
          </div>
          <div class="col-md-6">
            <strong><i class="fas fa-building"></i> Department:</strong> ${department}
          </div>
        </div>`;
    }
    
    if (diagnosis) {
      contentHtml += `
        <div class="row mb-3">
          <div class="col-12">
            <div class="alert alert-info">
              <strong>Diagnosis:</strong> ${diagnosis}
            </div>
          </div>
        </div>`;
    }
    
    if (content) {
      contentHtml += `
        <div class="row mb-3">
          <div class="col-12">
            <strong>Content/Notes:</strong>
            <div class="mt-2 p-3 bg-light rounded">
              <pre style="white-space: pre-wrap; font-size: 0.9rem; margin: 0;">${content}</pre>
            </div>
          </div>
        </div>`;
    }
    
    if (medicines && medicines.length > 0) {
      contentHtml += `
        <div class="row mb-3">
          <div class="col-12">
            <strong><i class="fas fa-pills"></i> Medications:</strong>
            <ul class="list-group mt-2">`;
      medicines.forEach(med => {
        const name = med.name || med.medicineName || "Unknown";
        const dosage = med.dosage || "";
        const frequency = med.frequency || "";
        const duration = med.duration || "";
        contentHtml += `
              <li class="list-group-item">
                <strong>${name}</strong>
                ${dosage ? `<br><small>Dosage: ${dosage}</small>` : ""}
                ${frequency ? `<br><small>Frequency: ${frequency}</small>` : ""}
                ${duration ? `<br><small>Duration: ${duration}</small>` : ""}
              </li>`;
      });
      contentHtml += `
            </ul>
          </div>
        </div>`;
    }
    
    if (testResults && testResults.length > 0) {
      contentHtml += `
        <div class="row mb-3">
          <div class="col-12">
            <strong><i class="fas fa-flask"></i> Test Results:</strong>
            <table class="table table-sm table-bordered mt-2">
              <thead>
                <tr>
                  <th>Test Name</th>
                  <th>Result</th>
                  <th>Unit</th>
                  <th>Reference Range</th>
                </tr>
              </thead>
              <tbody>`;
      testResults.forEach(test => {
        contentHtml += `
                <tr>
                  <td>${test.testName || test.name || "N/A"}</td>
                  <td><strong>${test.result || test.value || "N/A"}</strong></td>
                  <td>${test.unit || ""}</td>
                  <td><small class="text-muted">${test.referenceRange || test.normalRange || "N/A"}</small></td>
                </tr>`;
      });
      contentHtml += `
              </tbody>
            </table>
          </div>
        </div>`;
    }
    
    // Show raw data in collapsible section
    contentHtml += `
      <hr>
      <div class="row">
        <div class="col-12">
          <button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#rawDataCollapse">
            <i class="fas fa-code"></i> View Raw Data
          </button>
          <div class="collapse mt-2" id="rawDataCollapse">
            <div class="card card-body">
              <pre style="font-size: 0.8rem; max-height: 300px; overflow-y: auto;">${JSON.stringify(record, null, 2)}</pre>
            </div>
          </div>
        </div>
      </div>`;
    
    // Populate modal
    document.getElementById("externalRecordContent").innerHTML = contentHtml;
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById("externalRecordModal"));
    modal.show();
  } catch (error) {
    console.error("Error viewing external record:", error);
    utils.showError("Failed to display external record: " + error.message);
  }
}

// Make function globally accessible
window.viewExternalRecord = viewExternalRecord;

function bindEvents() {
  // Patient dropdown selection
  const patientDropdown = document.getElementById("patientDropdown");
  if (patientDropdown) {
    patientDropdown.addEventListener("change", (e) => {
      const selectedValue = e.target.value;
      if (!selectedValue) {
        selectedPatient = null;
        const summary = document.getElementById("patientSummary");
        if (summary) summary.classList.add("d-none");
        const loadBtn = document.getElementById("loadHistoryBtn");
        if (loadBtn) loadBtn.disabled = true;
        return;
      }

      const option = e.target.selectedOptions[0];
      const patient = JSON.parse(option.dataset.patientData);
      showPatientSummary(patient);
    });
  } else {
    console.warn("patientDropdown element not found");
  }

  // ABHA ID search button
  const abhaSearchBtn = document.getElementById("abhaSearchBtn");
  if (abhaSearchBtn) {
    abhaSearchBtn.addEventListener("click", searchByAbha);
  } else {
    console.warn("abhaSearchBtn element not found");
  }

  // ABHA ID search input
  const abhaSearchValue = document.getElementById("abhaSearchValue");
  if (abhaSearchValue) {
    abhaSearchValue.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        searchByAbha();
      }
    });
  } else {
    console.warn("abhaSearchValue element not found");
  }

  // Load history and refresh buttons
  const loadHistoryBtn = document.getElementById("loadHistoryBtn");
  if (loadHistoryBtn) {
    loadHistoryBtn.addEventListener("click", loadHistory);
  } else {
    console.warn("loadHistoryBtn element not found");
  }

  const refreshBtn = document.getElementById("refreshBtn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", loadHistory);
  } else {
    console.warn("refreshBtn element not found");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  console.log("DOM loaded, binding events and loading patients...");
  bindEvents();
  loadPatientsDropdown(); // Load patients on page load
});

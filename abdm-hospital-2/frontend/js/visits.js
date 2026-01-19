// visits.js - Visits Management

let currentVisit = null;
let allVisits = [];
let selectedPatient = null;

// Initialize page
document.addEventListener("DOMContentLoaded", function () {
  // Set default date to today - with a slight delay to ensure DOM is ready
  setTimeout(() => {
    const today = new Date().toISOString().split("T")[0];
    const dateInput = document.getElementById("visitDate");
    if (dateInput) {
      dateInput.value = today;
      console.log("Visit date set to:", today);
    } else {
      console.error("Visit date input not found!");
    }
  }, 100);

  // Load visits
  loadVisits();

  // Event listeners
  document
    .getElementById("createVisitForm")
    .addEventListener("submit", handleCreateVisit);

  // Patient search button
  document
    .getElementById("searchPatientBtn")
    .addEventListener("click", handleSearchPatient);

  // Enter key on patient search input
  document
    .getElementById("patientSearchInput")
    .addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleSearchPatient();
      }
    });

  // Check for patient_id in URL params
  const urlParams = new URLSearchParams(window.location.search);
  const patientId = urlParams.get("patient_id");
  if (patientId) {
    document.getElementById("patientId").value = patientId;
  }
});

// Load all visits
async function loadVisits() {
  try {
    utils.showLoading();
    const visits = await api.visits.list();
    allVisits = visits;
    renderVisitsTable(visits);
  } catch (error) {
    utils.showError("Failed to load visits: " + error.message);
    const activeBody = document.getElementById("activeVisitsTableBody");
    const completedBody = document.getElementById("completedVisitsTableBody");

    if (activeBody) {
      activeBody.innerHTML = `
        <tr>
          <td colspan="7" class="text-center text-danger">
            <i class="fas fa-exclamation-triangle"></i> Failed to load visits
          </td>
        </tr>
      `;
    }

    if (completedBody) {
      completedBody.innerHTML = `
        <tr>
          <td colspan="7" class="text-center text-danger">
            <i class="fas fa-exclamation-triangle"></i> Failed to load visits
          </td>
        </tr>
      `;
    }
  } finally {
    utils.hideLoading();
  }
}

// Render visits table - separated by status
function renderVisitsTable(visits) {
  // Separate visits into active and completed
  const activeVisits = visits.filter(
    (v) => v.status === "Scheduled" || v.status === "In Progress",
  );
  const completedVisits = visits.filter(
    (v) => v.status === "Completed" || v.status === "Cancelled",
  );

  // Render active visits
  const activeBody = document.getElementById("activeVisitsTableBody");
  if (activeVisits.length === 0) {
    activeBody.innerHTML = `
      <tr>
        <td colspan="7" class="text-center text-muted">
          <i class="fas fa-inbox"></i> No active visits
        </td>
      </tr>
    `;
  } else {
    activeBody.innerHTML = activeVisits
      .map((visit) => renderVisitRow(visit))
      .join("");
  }

  // Render completed visits
  const completedBody = document.getElementById("completedVisitsTableBody");
  if (completedVisits.length === 0) {
    completedBody.innerHTML = `
      <tr>
        <td colspan="7" class="text-center text-muted">
          <i class="fas fa-inbox"></i> No completed visits
        </td>
      </tr>
    `;
  } else {
    completedBody.innerHTML = completedVisits
      .map((visit) => renderVisitRow(visit))
      .join("");
  }
}

// Render individual visit row
function renderVisitRow(visit) {
  const statusClass = getStatusClass(visit.status);
  const visitDate = utils.formatDate(visit.visitDate || visit.visit_date);

  return `
    <tr>
      <td>
        <div>${visit.patientName || "N/A"}</div>
        <small class="text-muted">${visit.patientId}</small>
      </td>
      <td>${visitDate}</td>
      <td><span class="badge bg-info">${visit.visitType || "N/A"}</span></td>
      <td>${visit.department || "N/A"}</td>
      <td>${visit.doctorId || "N/A"}</td>
      <td><span class="badge ${statusClass}">${visit.status || "Unknown"}</span></td>
      <td>
        <button class="btn btn-sm btn-primary" onclick="viewVisit('${visit.visitId || visit.id}')">
          <i class="fas fa-eye"></i>
        </button>
      </td>
    </tr>
  `;
}

// Get status badge class
function getStatusClass(status) {
  const statusMap = {
    Scheduled: "bg-primary",
    "In Progress": "bg-warning",
    Completed: "bg-success",
    Cancelled: "bg-secondary",
  };
  return statusMap[status] || "bg-secondary";
}

// Handle create visit form submission
async function handleCreateVisit(e) {
  e.preventDefault();

  // Simple validation
  const patientId = document.getElementById("patientId").value.trim();
  const visitDate = document.getElementById("visitDate").value;
  const visitType = document.getElementById("visitType").value;
  const department = document.getElementById("department").value.trim();

  if (!patientId || !visitDate || !visitType) {
    utils.showError("Please fill in all required fields");
    return;
  }

  try {
    utils.showLoading();

    // Simple API call with status field
    await api.visits.create({
      patientId,
      visitDate,
      visitType,
      department: department || null,
      doctorId: document.getElementById("doctor").value.trim() || null,
      status: document.getElementById("status").value || "Scheduled",
    });

    utils.showSuccess("Visit created successfully!");

    // Show additional notification about automatic care context creation
    setTimeout(() => {
      utils.showInfo(
        "✅ Care context is being created and linked to ABDM Gateway automatically in the background",
      );
    }, 1000);

    // Clear form and reload
    e.target.reset();
    document.getElementById("visitDate").value = new Date()
      .toISOString()
      .split("T")[0];

    // Reset patient selection
    selectedPatient = null;
    document.getElementById("patientSearchInput").value = "";
    document.getElementById("patientDetailsDiv").style.display = "none";
    document.getElementById("patientId").value = "";
    document.getElementById("patientName").textContent = "";
    document.getElementById("patientMobile").textContent = "";
    document.getElementById("patientAbha").textContent = "";

    await loadVisits();
  } catch (error) {
    utils.showError("Failed to create visit: " + error.message);
  } finally {
    utils.hideLoading();
  }
}

// Handle patient search - by mobile or aadhaar
async function handleSearchPatient() {
  const searchInput = document
    .getElementById("patientSearchInput")
    .value.trim();
  const searchType = document.getElementById("searchType").value;

  if (!searchInput) {
    utils.showError("Please enter a search value");
    return;
  }

  try {
    utils.showLoading();
    const patients = await api.patients.list();

    console.log("All patients:", patients);
    console.log("Search type:", searchType);
    console.log("Search input:", searchInput);

    let foundPatient = null;

    if (searchType === "mobile") {
      // Search by mobile - exact match
      foundPatient = patients.find((p) => {
        const matches = String(p.mobile).trim() === String(searchInput).trim();
        console.log(`Comparing ${p.mobile} with ${searchInput}: ${matches}`);
        return matches;
      });
    } else {
      // Search by Aadhaar - match full or last 4 digits
      foundPatient = patients.find((p) => {
        if (!p.aadhaar) return false;
        const fullMatch =
          String(p.aadhaar).trim() === String(searchInput).trim();
        const lastFourMatch =
          searchInput.length === 4 &&
          String(p.aadhaar).slice(-4) === searchInput;
        const matches = fullMatch || lastFourMatch;
        console.log(
          `Aadhaar ${p.aadhaar}: full match=${fullMatch}, last4=${lastFourMatch}`,
        );
        return matches;
      });
    }

    console.log("Found patient:", foundPatient);

    if (foundPatient) {
      selectPatient(foundPatient);
    } else {
      utils.showError(`No patient found with ${searchType}: ${searchInput}`);
    }
  } catch (error) {
    console.error("Search error:", error);
    utils.showError("Error searching patient: " + error.message);
  } finally {
    utils.hideLoading();
  }
}

// Select patient and auto-fill form
function selectPatient(patient) {
  selectedPatient = patient;

  // Auto-fill patient details
  document.getElementById("patientId").value = patient.patientId;
  document.getElementById("patientName").textContent = patient.name;
  document.getElementById("patientMobile").textContent = patient.mobile;
  document.getElementById("patientAbha").textContent =
    patient.abhaId || "Not linked";
  document.getElementById("patientDetailsDiv").style.display = "block";

  // Clear search input
  document.getElementById("patientSearchInput").value = "";

  utils.showSuccess("Patient selected!");
}

// View visit details

// Apply filters
function applyFilters() {
  const startDate = document.getElementById("filterStartDate").value;
  const endDate = document.getElementById("filterEndDate").value;
  const type = document.getElementById("filterType").value;
  const status = document.getElementById("filterStatus").value;

  let filteredVisits = [...allVisits];

  // Filter by date range
  if (startDate) {
    filteredVisits = filteredVisits.filter((v) => v.visit_date >= startDate);
  }
  if (endDate) {
    filteredVisits = filteredVisits.filter((v) => v.visit_date <= endDate);
  }

  // Filter by type
  if (type) {
    filteredVisits = filteredVisits.filter((v) => v.visit_type === type);
  }

  // Filter by status
  if (status) {
    filteredVisits = filteredVisits.filter((v) => v.status === status);
  }

  renderVisitsTable(filteredVisits);
}

// Clear filters
function clearFilters() {
  document.getElementById("filterStartDate").value = "";
  document.getElementById("filterEndDate").value = "";
  document.getElementById("filterType").value = "";
  document.getElementById("filterStatus").value = "";
  renderVisitsTable(allVisits);
}

// View visit details
async function viewVisit(visitId) {
  try {
    utils.showLoading();

    console.log("Searching for visitId:", visitId);
    console.log("All visits in array:", allVisits);

    // Convert visitId to string for comparison
    const visitIdStr = String(visitId).trim();

    // Find visit in current list - check both camelCase and snake_case keys
    const visit = allVisits.find((v) => {
      const matches =
        String(v.visitId || v.visit_id || v.id).trim() === visitIdStr;
      console.log(
        `Comparing visit: visitId="${v.visitId}", visit_id="${v.visit_id}", id="${v.id}" -> ${matches}`,
      );
      return matches;
    });

    if (!visit) {
      console.error("Visit not found. Looking for visitId:", visitId);
      console.log("All visits:", allVisits);
      utils.showError("Visit not found");
      return;
    }

    console.log("Found visit:", visit);
    currentVisit = visit;

    // Populate modal - use camelCase keys from API
    document.getElementById("detailVisitId").textContent =
      visit.visitId || visit.visit_id || visit.id;
    document.getElementById("detailStatus").textContent =
      visit.status || "Unknown";
    document.getElementById("detailStatus").className =
      "badge " + getStatusClass(visit.status);
    document.getElementById("detailPatientId").textContent =
      visit.patientId || visit.patient_id;
    document.getElementById("detailPatientName").textContent =
      visit.patientName || visit.patient_name || "N/A";
    document.getElementById("detailVisitDate").textContent = utils.formatDate(
      visit.visitDate || visit.visit_date,
    );
    document.getElementById("detailVisitType").textContent =
      visit.visitType || visit.visit_type || "N/A";
    document.getElementById("detailDepartment").textContent =
      visit.department || "N/A";
    document.getElementById("detailDoctor").textContent =
      visit.doctorId || visit.doctor || "N/A";
    document.getElementById("detailReason").textContent =
      visit.reason || "No reason provided";
    document.getElementById("detailCreatedAt").textContent =
      utils.formatDate(visit.createdAt || visit.created_at) || "N/A";
    document.getElementById("detailUpdatedAt").textContent =
      utils.formatDate(visit.updatedAt || visit.updated_at) || "N/A";

    // Disable health record button for completed or cancelled visits
    const isCompletedOrCancelled =
      visit.status === "Completed" || visit.status === "Cancelled";
    const addHealthRecordBtn = document.getElementById("addHealthRecordBtn");

    if (isCompletedOrCancelled) {
      addHealthRecordBtn.disabled = true;
      addHealthRecordBtn.classList.add("opacity-50");
      addHealthRecordBtn.title =
        "Cannot add health records to completed/cancelled visits";
    } else {
      addHealthRecordBtn.disabled = false;
      addHealthRecordBtn.classList.remove("opacity-50");
      addHealthRecordBtn.title = "";
    }

    // Show modal
    const modal = new bootstrap.Modal(
      document.getElementById("visitDetailsModal"),
    );
    modal.show();
  } catch (error) {
    utils.showError("Failed to load visit details: " + error.message);
  } finally {
    utils.hideLoading();
  }
}

// Create care context for visit
function createCareContextForVisit() {
  if (!currentVisit) return;

  // Navigate to care contexts page with visit info
  window.location.href = `care-contexts.html?patient_id=${currentVisit.patient_id}&visit_id=${currentVisit.visit_id || currentVisit.id}`;
}

// Add health record for visit
function addHealthRecordForVisit() {
  if (!currentVisit) return;

  // Navigate to health records page with visit info
  window.location.href = `health-records.html?patient_id=${currentVisit.patient_id}&visit_id=${currentVisit.visit_id || currentVisit.id}`;
}

// Make functions globally accessible
window.viewVisit = viewVisit;
window.selectPatient = selectPatient;

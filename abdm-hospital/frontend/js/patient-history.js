// patient-history.js - view patient visits and health records

let selectedPatient = null;
let visitsCache = [];
let recordsCache = [];

function setLoading(isLoading) {
  const btn = document.getElementById("loadHistoryBtn");
  if (btn) btn.disabled = isLoading || !selectedPatient;
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
  const body = document.getElementById("recordsBody");
  if (!body) return;
  if (!records || records.length === 0) {
    body.innerHTML = `
      <tr>
        <td colspan="4" class="text-center text-muted">
          <i class="fas fa-inbox"></i> No records found
        </td>
      </tr>`;
    return;
  }
  body.innerHTML = records
    .map((r) => {
      const date = utils.formatDate(r.record_date || r.recordDate);
      const type = r.record_type || r.recordType || "Unknown";
      const source = r.source_hospital || r.sourceHospital || "Local";
      return `
        <tr>
          <td>${date || "-"}</td>
          <td>${type}</td>
          <td>${source}</td>
          <td>
            <button class="btn btn-sm btn-outline-primary" onclick='alert(${JSON.stringify("See full record in API response")})'>
              <i class="fas fa-eye"></i>
            </button>
          </td>
        </tr>`;
    })
    .join("");
}

async function searchPatient() {
  const type = document.getElementById("searchType").value;
  const value = document.getElementById("searchValue").value.trim();
  if (!value) {
    utils.showError("Enter a value to search");
    return;
  }
  try {
    utils.showLoading();
    const patients = await api.patients.list();
    let found = null;
    if (type === "mobile") {
      found = patients.find((p) => String(p.mobile).trim() === value);
    } else if (type === "aadhaar") {
      found = patients.find((p) => String(p.aadhaar || "").trim() === value);
    } else {
      found = patients.find(
        (p) => String(p.patientId || p.id).trim() === value,
      );
    }
    if (!found) {
      utils.showError("Patient not found");
      return;
    }
    selectedPatient = found;
    document.getElementById("pName").textContent = found.name || "";
    document.getElementById("pMobile").textContent = found.mobile || "";
    document.getElementById("pAbha").textContent = found.abhaId || "Not linked";
    document.getElementById("pId").textContent = found.patientId || found.id;
    document.getElementById("patientSummary").classList.remove("d-none");
    document.getElementById("loadHistoryBtn").disabled = false;
    utils.showSuccess("Patient selected");
  } catch (err) {
    utils.showError("Search failed: " + err.message);
  } finally {
    utils.hideLoading();
  }
}

async function loadHistory() {
  if (!selectedPatient) {
    utils.showError("Select a patient first");
    return;
  }
  try {
    setLoading(true);
    utils.showInfo("Requesting visits and records...");

    // Load visits (local)
    const visitsRes = await api.visits.getByPatient(
      selectedPatient.patientId || selectedPatient.id,
    );
    visitsCache = visitsRes.visits || visitsRes || [];
    renderVisits(visitsCache);

    // Load health records (local + external if backend merged)
    const records = await api.healthRecords.getByPatient(
      selectedPatient.patientId || selectedPatient.id,
    );
    recordsCache = records || [];
    renderRecords(recordsCache);

    document.getElementById("historyStatus").innerHTML =
      '<div class="alert alert-success mb-0">History loaded. Remote records will appear once delivered via webhook.</div>';
  } catch (err) {
    document.getElementById("historyStatus").innerHTML =
      `<div class="alert alert-danger mb-0">Failed to load history: ${err.message}</div>`;
  } finally {
    setLoading(false);
  }
}

function bindEvents() {
  document.getElementById("searchBtn").addEventListener("click", searchPatient);
  document
    .getElementById("loadHistoryBtn")
    .addEventListener("click", loadHistory);
  document.getElementById("refreshBtn").addEventListener("click", loadHistory);
  document.getElementById("searchValue").addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      searchPatient();
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
});

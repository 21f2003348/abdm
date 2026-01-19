// Patients page functionality
let currentPatient = null;

document.addEventListener("DOMContentLoaded", function () {
  loadPatients();

  // Register patient form
  document
    .getElementById("registerPatientForm")
    .addEventListener("submit", handleRegisterPatient);

  // Search patient form
  document
    .getElementById("searchPatientForm")
    .addEventListener("submit", handleSearchPatient);
});

async function loadPatients() {
  const container = document.getElementById("patientsList");

  try {
    container.innerHTML =
      '<div class="text-center text-muted py-4"><div class="spinner-border spinner-border-sm me-2"></div>Loading patients...</div>';

    const patients = await api.patients.list();

    if (!patients || patients.length === 0) {
      container.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="fas fa-users fa-4x mb-3"></i>
                    <h5>No Patients Registered Yet</h5>
                    <p>Register your first patient using the form on the left</p>
                </div>
            `;
      return;
    }

    container.innerHTML = `
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Mobile</th>
                            <th>ABHA ID</th>
                            <th>Aadhaar</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${patients
                          .map(
                            (patient) => `
                            <tr>
                                <td><i class="fas fa-user text-primary"></i> ${patient.name}</td>
                                <td>${patient.mobile}</td>
                                <td>${patient.abhaId ? `<span class="badge bg-success">${patient.abhaId}</span>` : '<span class="text-muted">-</span>'}</td>
                                <td>${patient.aadhaar ? patient.aadhaar.slice(0, 4) + "****" + patient.aadhaar.slice(-4) : '<span class="text-muted">-</span>'}</td>
                                <td>
                                    <button class="btn btn-sm btn-outline-primary" onclick='viewPatient(${JSON.stringify(patient)})'>
                                        <i class="fas fa-eye"></i> View
                                    </button>
                                </td>
                            </tr>
                        `,
                          )
                          .join("")}
                    </tbody>
                </table>
            </div>
        `;
  } catch (error) {
    container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i> Error loading patients: ${error.message}
            </div>
        `;
  }
}

async function handleRegisterPatient(e) {
  e.preventDefault();

  const name = document.getElementById("patientName").value;
  const mobile = document.getElementById("patientMobile").value;
  const abhaId = document.getElementById("patientAbhaId").value;
  const aadhaar = document.getElementById("patientAadhaar").value;

  try {
    utils.showLoading();

    const data = {
      name,
      mobile,
      ...(abhaId && { abhaId }),
      ...(aadhaar && { aadhaar }),
    };

    const response = await api.patients.register(data);

    utils.hideLoading();
    utils.showSuccess(`Patient ${name} registered successfully!`);

    // Reset form
    document.getElementById("registerPatientForm").reset();

    // Reload patients list
    await loadPatients();
  } catch (error) {
    utils.hideLoading();
    utils.showError(`Error registering patient: ${error.message}`);
  }
}

async function handleSearchPatient(e) {
  e.preventDefault();

  const mobile = document.getElementById("searchMobile").value.trim();
  const resultsContainer = document.getElementById("searchResults");

  try {
    resultsContainer.innerHTML =
      '<div class="spinner-border spinner-border-sm"></div> Searching...';

    console.log("Searching for mobile:", mobile);
    const response = await api.patients.search(mobile);
    console.log("Search response:", response);

    if (response.found) {
      const patient = response.patient;
      resultsContainer.innerHTML = `
                <div class="alert alert-success">
                    <h6><i class="fas fa-check-circle"></i> Patient Found</h6>
                    <p class="mb-1"><strong>Name:</strong> ${patient.name}</p>
                    <p class="mb-1"><strong>Mobile:</strong> ${patient.mobile}</p>
                    ${patient.abhaId ? `<p class="mb-1"><strong>ABHA ID:</strong> ${patient.abhaId}</p>` : ""}
                    <button class="btn btn-sm btn-primary mt-2" onclick='viewPatient(${JSON.stringify(patient)})'>
                        <i class="fas fa-eye"></i> View Full Details
                    </button>
                </div>
            `;
    } else {
      resultsContainer.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-info-circle"></i> No patient found with mobile number: ${mobile}
                </div>
            `;
    }
  } catch (error) {
    resultsContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i> Error: ${error.message}
            </div>
        `;
  }
}

function viewPatient(patient) {
  currentPatient = patient;

  const modalContent = document.getElementById("patientDetailsContent");
  modalContent.innerHTML = `
        <div class="row">
            <div class="col-md-6 mb-3">
                <h6 class="text-muted">Basic Information</h6>
                <table class="table table-sm">
                    <tr>
                        <td><strong>Patient ID:</strong></td>
                        <td>${patient.patientId}</td>
                    </tr>
                    <tr>
                        <td><strong>Name:</strong></td>
                        <td>${patient.name}</td>
                    </tr>
                    <tr>
                        <td><strong>Mobile:</strong></td>
                        <td>${patient.mobile}</td>
                    </tr>
                </table>
            </div>
            <div class="col-md-6 mb-3">
                <h6 class="text-muted">ABDM Information</h6>
                <table class="table table-sm">
                    <tr>
                        <td><strong>ABHA ID:</strong></td>
                        <td>${patient.abhaId || '<span class="text-muted">Not linked</span>'}</td>
                    </tr>
                    <tr>
                        <td><strong>Aadhaar:</strong></td>
                        <td>${patient.aadhaar ? patient.aadhaar.slice(0, 4) + "****" + patient.aadhaar.slice(-4) : '<span class="text-muted">Not provided</span>'}</td>
                    </tr>
                </table>
            </div>
        </div>
        <hr>
        <h6 class="text-muted mb-3">Recent Activity</h6>
        <div id="patientActivity">
            <div class="spinner-border spinner-border-sm"></div> Loading activity...
        </div>
    `;

  const modal = new bootstrap.Modal(
    document.getElementById("patientDetailsModal"),
  );
  modal.show();

  // Load patient activity (visits, records, etc.)
  loadPatientActivity(patient.patientId);
}

async function loadPatientActivity(patientId) {
  const container = document.getElementById("patientActivity");

  try {
    const [visits] = await Promise.all([
      api.visits.getByPatient(patientId).catch(() => ({ visits: [] })),
    ]);

    if (visits.visits && visits.visits.length > 0) {
      container.innerHTML = `
                <div class="list-group">
                    ${visits.visits
                      .map(
                        (visit) => `
                        <div class="list-group-item">
                            <div class="d-flex justify-content-between">
                                <h6 class="mb-1"><i class="fas fa-calendar"></i> ${visit.visitType || "Visit"}</h6>
                                <small class="text-muted">${utils.formatDateOnly(visit.visitDate)}</small>
                            </div>
                            <p class="mb-1 text-muted small">${visit.reason || "No reason provided"}</p>
                        </div>
                    `,
                      )
                      .join("")}
                </div>
            `;
    } else {
      container.innerHTML = '<p class="text-muted">No visits recorded yet</p>';
    }
  } catch (error) {
    container.innerHTML = `<div class="alert alert-danger">Error loading activity</div>`;
  }
}

function createVisitForPatient() {
  if (currentPatient) {
    window.location.href = `visits.html?patientId=${currentPatient.patientId}`;
  }
}

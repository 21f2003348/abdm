// API Base URL
const API_BASE_URL = "http://127.0.0.1:8080";

// API Helper Functions
const api = {
  // Generic GET request
  async get(endpoint) {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error("GET request failed:", error);
      throw error;
    }
  },

  // Generic POST request
  async post(endpoint, data) {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || `HTTP error! status: ${response.status}`,
        );
      }
      return await response.json();
    } catch (error) {
      console.error("POST request failed:", error);
      throw error;
    }
  },

  // Generic PATCH request
  async patch(endpoint, data) {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error("PATCH request failed:", error);
      throw error;
    }
  },

  // Generic DELETE request
  async delete(endpoint) {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error("DELETE request failed:", error);
      throw error;
    }
  },

  // Health check
  async healthCheck() {
    return this.get("/health");
  },

  // Gateway health check
  async gatewayHealthCheck() {
    return this.get("/gateway-health");
  },

  // Patient APIs
  patients: {
    async register(data) {
      return api.post("/api/patient/register", data);
    },
    async search(mobile) {
      // Search endpoint doesn't exist - we'll need to add it or use list and filter
      const patients = await api.get("/api/patient/list");
      console.log("All patients:", patients);
      console.log("Searching for mobile:", mobile);
      const patient = patients.find(
        (p) => String(p.mobile).trim() === String(mobile).trim(),
      );
      console.log("Found patient:", patient);

      if (patient) {
        return { found: true, patient };
      } else {
        return { found: false };
      }
    },
    async list() {
      return api.get("/api/patient/list");
    },
  },

  // Visit APIs
  visits: {
    async create(data) {
      return api.post("/api/visit/create", data);
    },
    async getByPatient(patientId) {
      const visits = await api.get(`/api/visit/patient/${patientId}`);
      return { visits };
    },
    async list() {
      return api.get("/api/visit/list");
    },
  },

  // Care Context APIs
  careContexts: {
    async createAndLink(data) {
      return api.post("/api/care-context/create-and-link", data);
    },
    async getByPatient(patientId) {
      return api.get(`/api/care-contexts/${patientId}`);
    },
  },

  // Health Records APIs
  healthRecords: {
    async create(data) {
      return api.post(`/api/health-records/${data.patient_id}`, data);
    },
    async getByPatient(patientId) {
      return api.get(`/api/health-records/${patientId}`);
    },
    async list() {
      return api.get("/api/health-records/");
    },
  },

  // Webhook APIs
  webhooks: {
    async getQueue() {
      return api.get("/webhook/queue");
    },
    async clearQueue() {
      return api.delete("/webhook/queue");
    },
  },

  // Demo API
  async testEndToEnd() {
    return this.post("/demo/test-end-to-end", {});
  },
};

// Utility Functions
const utils = {
  // Show loading spinner
  showLoading() {
    const overlay = document.createElement("div");
    overlay.className = "spinner-overlay";
    overlay.id = "loadingOverlay";
    overlay.innerHTML =
      '<div class="spinner-border text-light" role="status"><span class="visually-hidden">Loading...</span></div>';
    document.body.appendChild(overlay);
  },

  // Hide loading spinner
  hideLoading() {
    const overlay = document.getElementById("loadingOverlay");
    if (overlay) {
      overlay.remove();
    }
  },

  // Show success toast
  showSuccess(message) {
    this.showToast(message, "success");
  },

  // Show error toast
  showError(message) {
    this.showToast(message, "danger");
  },

  // Show info toast
  showInfo(message) {
    this.showToast(message, "info");
  },

  // Generic toast notification
  showToast(message, type = "info") {
    const toastContainer =
      document.getElementById("toastContainer") || this.createToastContainer();

    const toast = document.createElement("div");
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute("role", "alert");
    toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    toast.addEventListener("hidden.bs.toast", () => {
      toast.remove();
    });
  },

  // Create toast container
  createToastContainer() {
    const container = document.createElement("div");
    container.id = "toastContainer";
    container.className = "toast-container position-fixed top-0 end-0 p-3";
    container.style.zIndex = "9999";
    document.body.appendChild(container);
    return container;
  },

  // Format date
  formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  },

  // Format date only
  formatDateOnly(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  },

  // Generate UUID
  generateUUID() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
      /[xy]/g,
      function (c) {
        const r = (Math.random() * 16) | 0;
        const v = c == "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
      },
    );
  },
};

// Export for use in other scripts
window.api = api;
window.utils = utils;

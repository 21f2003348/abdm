# ABDM Hospital Frontend

## Overview

A clean, responsive web interface for managing hospital operations and ABDM integration using plain HTML, CSS, JavaScript, and Bootstrap 5.

## Features

### ✅ Implemented

1. **Dashboard** (index.html)
   - Real-time statistics (patients, visits, care contexts)
   - ABDM gateway status monitoring
   - Quick action buttons
   - Recent activity feed

2. **Patient Management** (patients.html)
   - Register new patients
   - Search patients by mobile
   - View patient list
   - Patient details modal

### 🚧 To Be Created

3. **Visit Management** (visits.html)
4. **Care Context Management** (care-contexts.html)
5. **Health Records** (health-records.html)
6. **ABDM Status Dashboard** (abdm-status.html)

## How to Use

### Starting the Application

1. **Start the Hospital Server:**

   ```bash
   cd abdm-hospital
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
   ```

2. **Access the Frontend:**
   Open your browser and navigate to:
   ```
   http://localhost:8080
   ```

### File Structure

```
frontend/
├── index.html              # Dashboard
├── patients.html           # Patient management
├── visits.html             # Visit management (to be created)
├── care-contexts.html      # Care context linking (to be created)
├── health-records.html     # Health records (to be created)
├── abdm-status.html        # ABDM integration status (to be created)
├── css/
│   └── style.css           # Custom styles
└── js/
    ├── api.js              # API helper functions
    ├── dashboard.js        # Dashboard logic
    └── patients.js         # Patient management logic
```

## API Integration

The frontend connects to the FastAPI backend at `http://localhost:8080` and uses the following endpoints:

- `GET /health` - Health check
- `GET /gateway-health` - Gateway status
- `POST /api/patients/register` - Register patient
- `GET /api/patients/search?mobile={mobile}` - Search patient
- `GET /api/patients/list` - List all patients
- `POST /api/visits/create` - Create visit
- `GET /api/visits/patient/{patientId}` - Get patient visits
- `GET /webhook/queue` - Get webhook queue
- `DELETE /webhook/queue` - Clear webhook queue

## Features in Detail

### Dashboard

- **Statistics Cards**: Shows total patients, active visits, care contexts, and ABDM connection status
- **Quick Actions**: Fast access to common tasks (register patient, create visit, etc.)
- **Recent Activity**: Lists recently registered patients and webhook notifications
- **Auto-refresh**: Updates every 30 seconds

### Patient Management

- **Registration Form**:
  - Required: Name, Mobile (10 digits)
  - Optional: ABHA ID, Aadhaar number
- **Search**: Find patients by mobile number
- **Patient List**: Sortable table with all registered patients
- **Patient Details**: Modal showing complete patient information and activity

## Customization

### Styling

Edit `css/style.css` to customize:

- Colors (primary, success, info, warning)
- Card styles
- Button styles
- Responsive breakpoints

### API Base URL

If your backend is on a different host/port, edit `js/api.js`:

```javascript
const API_BASE_URL = "http://your-server:port";
```

## Browser Compatibility

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Development Tips

### Adding New Pages

1. Create HTML file in `frontend/` directory
2. Include navigation bar (copy from existing page)
3. Create corresponding JS file in `js/` directory
4. Add API functions in `js/api.js` if needed

### Debugging

- Open browser DevTools (F12)
- Check Console for JavaScript errors
- Check Network tab for API call issues

## Next Steps

To complete the frontend, create these remaining pages:

1. **visits.html** - Visit/appointment management
2. **care-contexts.html** - Link care contexts to ABDM
3. **health-records.html** - Upload and manage health records
4. **abdm-status.html** - Monitor ABDM integration, webhooks, linking status

Would you like me to create any of these pages next?

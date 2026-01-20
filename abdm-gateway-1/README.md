# ABDM Gateway

## Overview

The ABDM Gateway is a backend service designed to handle various API routes and services for the ABDM ecosystem. This document provides instructions on how to set up and start the application.

---

## Prerequisites

1. **Python**: Ensure Python 3.8 or higher is installed on your system.
   - You can download Python from [python.org](https://www.python.org/).
2. **Pip**: Ensure `pip` (Python package manager) is installed.
3. **Virtual Environment** (optional but recommended): Use a virtual environment to isolate dependencies.

---

## Installation Steps

1. **Clone the Repository**:

   ```bash
   git clone <repository-url>
   cd abdm-gateway
   ```

2. **Set Up a Virtual Environment** (optional):

   ```bash
   python -m venv venv
   venv\Scripts\Activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## Starting the Application

1. **Activate the Virtual Environment**:

   ```bash
   .venv/Scripts/Activate
   ```

2. **Run the Application with Uvicorn**:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Access the API**:
   - The application will start on `http://127.0.0.1:8000` by default.
   - Logs will indicate the startup process, including the environment and server details.
   - Use tools like Postman or a browser to interact with the API.

---

## Additional Notes

- **Configuration**:
  - Modify settings in `app/core/config.py` as needed.
- **Logs**:
  - Logs are managed in `app/core/logging.py`.
- **API Documentation**:
  - Refer to the `md-files/` directory for detailed API mappings and summaries.

---

## Troubleshooting

- If you encounter issues, ensure all dependencies are installed correctly.
- Check the Python version and virtual environment activation.
- Refer to the logs for detailed error messages.

---

## Contributing

Contributions are welcome! Please follow the standard Git workflow:

1. Fork the repository.
2. Create a feature branch.
3. Submit a pull request.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

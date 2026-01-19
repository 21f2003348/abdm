#!/usr/bin/env python3
"""
Comprehensive ABDM System Initialization for Hospital 1.
Initializes database, creates default data, sets up authentication with gateway,
manages bridge registration, handles consent, and generates .env configuration.
Run this ONCE after system setup to fully initialize the hospital.

Usage:
    python init_abdm_system.py
"""

import os
import sys
import json
import uuid
import secrets
import requests
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv, set_key

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import Base, engine, SessionLocal
from app.database.models import Patient, Visit, CareContext, HealthRecord

# ============================================================================
# CONFIGURATION
# ============================================================================

GATEWAY_URL = os.getenv("GATEWAY_BASE_URL", "http://localhost:8000")
HOSPITAL_NAME = "City Medical Center - Hospital 1"
HOSPITAL_PORT = 8080
HOSPITAL_URL = f"http://localhost:{HOSPITAL_PORT}"
HOSPITAL_WEBHOOK_URL = f"{HOSPITAL_URL}/webhook"

# Default client credentials for this hospital
DEFAULT_CLIENT_ID = "client-002"
DEFAULT_CLIENT_SECRET = "secret-002"

# Bridge details for HIP (Health Information Provider)
DEFAULT_BRIDGE_ID_HIP = "hiu-001"
DEFAULT_BRIDGE_ID_HIU = "hiu-001"
DEFAULT_ENTITY_TYPE = "HIU"
DEFAULT_X_CM_ID = "hospital-1"

# ============================================================================
# DEFAULT DATA SETS
# ============================================================================

PATIENTS_DATA = [
    {
        "name": "Rajesh Kumar",
        "mobile": "9876543210",
        "aadhaar": "123456789012",
        "abha_id": "rajesh.kumar@sbx"
    },
    {
        "name": "Priya Singh",
        "mobile": "9876543211",
        "aadhaar": "123456789013",
        "abha_id": "priya.singh@sbx"
    },
    {
        "name": "Amit Patel",
        "mobile": "9876543212",
        "aadhaar": "123456789014",
        "abha_id": "amit.patel@sbx"
    },
    {
        "name": "Neha Sharma",
        "mobile": "9876543213",
        "aadhaar": "123456789015",
        "abha_id": "neha.sharma@sbx"
    }
]

VISITS_TEMPLATE = {
    0: [  # Rajesh Kumar - Cardiology
        {
            "visit_type": "OPD",
            "department": "Cardiology",
            "doctor_id": "DR001",
            "days_offset": -7,
            "status": "Completed"
        },
        {
            "visit_type": "OPD",
            "department": "Cardiology",
            "doctor_id": "DR001",
            "days_offset": 5,
            "status": "Scheduled"
        }
    ],
    1: [  # Priya Singh - Orthopedics
        {
            "visit_type": "IPD",
            "department": "Orthopedics",
            "doctor_id": "DR002",
            "days_offset": -3,
            "status": "Completed"
        }
    ],
    2: [  # Amit Patel - General Medicine
        {
            "visit_type": "OPD",
            "department": "General Medicine",
            "doctor_id": "DR003",
            "days_offset": 0,
            "status": "In Progress"
        },
        {
            "visit_type": "OPD",
            "department": "General Medicine",
            "doctor_id": "DR003",
            "days_offset": 10,
            "status": "Scheduled"
        }
    ],
    3: [  # Neha Sharma - Neurology
        {
            "visit_type": "OPD",
            "department": "Neurology",
            "doctor_id": "DR004",
            "days_offset": -5,
            "status": "Completed"
        }
    ]
}

CARE_CONTEXTS_TEMPLATE = {
    0: {
        "context_name": "Cardiac Care - 2026",
        "description": "Comprehensive cardiac monitoring and treatment program"
    },
    1: {
        "context_name": "Orthopedic Treatment - 2026",
        "description": "Post-surgery orthopedic care and rehabilitation"
    },
    2: {
        "context_name": "General Health Checkup - 2026",
        "description": "Annual health checkup and preventive screening"
    },
    3: {
        "context_name": "Neurology Care - 2026",
        "description": "Neurological assessment and treatment"
    }
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def print_header(text: str):
    """Print formatted header"""
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}")

def print_section(text: str):
    """Print formatted section"""
    print(f"\n📋 {text}")
    print(f"{'-' * 70}")

def print_success(text: str):
    """Print success message"""
    print(f"✅ {text}")

def print_info(text: str):
    """Print info message"""
    print(f"ℹ️  {text}")

def print_warning(text: str):
    """Print warning message"""
    print(f"⚠️  {text}")

def print_error(text: str):
    """Print error message"""
    print(f"❌ {text}")

# ============================================================================
# ENVIRONMENT & CONFIGURATION MANAGEMENT
# ============================================================================

def generate_secure_secret(length: int = 32) -> str:
    """Generate a secure random secret"""
    return secrets.token_urlsafe(length)

def load_or_create_env_file() -> Dict[str, str]:
    """Load existing .env or create new one"""
    env_path = Path(os.path.dirname(__file__)) / ".env"
    
    env_vars = {}
    if env_path.exists():
        load_dotenv(env_path)
        print_info(f"Loaded existing .env file from {env_path}")
    else:
        print_info(f"Creating new .env file at {env_path}")
    
    return env_vars

def save_env_variable(key: str, value: str):
    """Save a single environment variable to .env"""
    env_path = Path(os.path.dirname(__file__)) / ".env"
    set_key(str(env_path), key, str(value))

def print_env_file():
    """Display contents of .env file"""
    env_path = Path(os.path.dirname(__file__)) / ".env"
    if env_path.exists():
        print_section("Generated .env Configuration")
        with open(env_path, 'r') as f:
            content = f.read()
            # Mask sensitive values
            lines = content.split('\n')
            for line in lines:
                if '=' in line:
                    key, value = line.split('=', 1)
                    if any(sensitive in key.upper() for sensitive in ['SECRET', 'PASSWORD', 'TOKEN']):
                        print(f"  {key}=***{'*' * max(0, len(value) - 8)}")
                    else:
                        print(f"  {line}")
                elif line.strip():
                    print(f"  {line}")

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_database():
    """Initialize database tables"""
    print_section("Database Initialization")
    
    try:
        Base.metadata.create_all(bind=engine)
        print_success("Database tables created successfully")
        return True
    except Exception as e:
        print_error(f"Failed to create database tables: {e}")
        return False

# ============================================================================
# PATIENT & HEALTH DATA SEEDING
# ============================================================================

def seed_patients() -> list:
    """Create default patients"""
    print_section("Creating Default Patients")
    
    db = SessionLocal()
    try:
        # Check if patients already exist
        existing = db.query(Patient).count()
        if existing > 0:
            print_warning(f"Database already contains {existing} patients. Skipping patient creation.")
            db.close()
            return db.query(Patient).all()
        
        patients = []
        for data in PATIENTS_DATA:
            patient = Patient(
                id=uuid.uuid4(),
                name=data["name"],
                mobile=data["mobile"],
                aadhaar=data["aadhaar"],
                abha_id=data["abha_id"]
            )
            db.add(patient)
            patients.append(patient)
            print_info(f"Created patient: {patient.name} ({patient.abha_id})")
        
        db.commit()
        print_success(f"Created {len(patients)} patients")
        return patients
    
    except Exception as e:
        print_error(f"Failed to create patients: {e}")
        db.rollback()
        return []
    finally:
        db.close()

def seed_visits(patients: list) -> list:
    """Create default visits linked to patients"""
    print_section("Creating Default Visits")
    
    db = SessionLocal()
    try:
        existing = db.query(Visit).count()
        if existing > 0:
            print_warning(f"Database already contains {existing} visits. Skipping visit creation.")
            db.close()
            return db.query(Visit).all()
        
        visits = []
        for patient_idx, patient in enumerate(patients):
            if patient_idx not in VISITS_TEMPLATE:
                continue
            
            for visit_data in VISITS_TEMPLATE[patient_idx]:
                visit_date = datetime.now(timezone.utc) + timedelta(days=visit_data["days_offset"])
                
                visit = Visit(
                    id=uuid.uuid4(),
                    patient_id=patient.id,
                    visit_type=visit_data["visit_type"],
                    department=visit_data["department"],
                    doctor_id=visit_data["doctor_id"],
                    visit_date=visit_date,
                    status=visit_data["status"]
                )
                db.add(visit)
                visits.append(visit)
                print_info(f"  {patient.name}: {visit_data['department']} ({visit_data['status']})")
        
        db.commit()
        print_success(f"Created {len(visits)} visits")
        return visits
    
    except Exception as e:
        print_error(f"Failed to create visits: {e}")
        db.rollback()
        return []
    finally:
        db.close()

def seed_care_contexts(patients: list) -> list:
    """Create care contexts linked to patients"""
    print_section("Creating Care Contexts")
    
    db = SessionLocal()
    try:
        existing = db.query(CareContext).count()
        if existing > 0:
            print_warning(f"Database already contains {existing} care contexts. Skipping creation.")
            db.close()
            return db.query(CareContext).all()
        
        care_contexts = []
        for patient_idx, patient in enumerate(patients):
            if patient_idx not in CARE_CONTEXTS_TEMPLATE:
                continue
            
            context_data = CARE_CONTEXTS_TEMPLATE[patient_idx]
            care_context = CareContext(
                id=uuid.uuid4(),
                patient_id=patient.id,
                context_name=context_data["context_name"],
                description=context_data["description"]
            )
            db.add(care_context)
            care_contexts.append(care_context)
            print_info(f"  {patient.name}: {context_data['context_name']}")
        
        db.commit()
        print_success(f"Created {len(care_contexts)} care contexts")
        return care_contexts
    
    except Exception as e:
        print_error(f"Failed to create care contexts: {e}")
        db.rollback()
        return []
    finally:
        db.close()

def seed_health_records(patients: list) -> list:
    """Create health records linked to patients and care contexts"""
    print_section("Creating Health Records")
    
    db = SessionLocal()
    try:
        existing = db.query(HealthRecord).count()
        if existing > 0:
            print_warning(f"Database already contains {existing} health records. Skipping creation.")
            db.close()
            return db.query(HealthRecord).all()
        
        health_records = []
        
        # Rajesh Kumar - Cardiac records
        if len(patients) > 0:
            patient = db.query(Patient).filter_by(id=patients[0].id).first()
            
            # Prescription
            hr1 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="PRESCRIPTION",
                record_date=datetime.now(timezone.utc) - timedelta(days=7),
                data_json={
                    "medications": [
                        {
                            "name": "Atenolol 50mg",
                            "dosage": "1 tablet daily",
                            "duration": "30 days",
                            "instructions": "Take in the morning after breakfast"
                        },
                        {
                            "name": "Aspirin 75mg",
                            "dosage": "1 tablet daily",
                            "duration": "30 days",
                            "instructions": "Take with dinner"
                        }
                    ],
                    "doctor": "Dr. Sharma (Cardiologist)",
                    "department": "Cardiology",
                    "diagnosis": "Hypertension with stable angina",
                    "followUpDate": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
                },
                data_text="Cardiac Prescription: Atenolol 50mg and Aspirin 75mg",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr1)
            health_records.append(hr1)
            
            # Diagnostic report
            hr2 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="DIAGNOSTIC_REPORT",
                record_date=datetime.now(timezone.utc) - timedelta(days=7),
                data_json={
                    "reportType": "ECG",
                    "testName": "Electrocardiogram",
                    "findings": "Normal sinus rhythm. No ST-T changes. HR: 72 bpm",
                    "interpretation": "Normal ECG",
                    "performedBy": "Dr. Mehta",
                    "department": "Cardiology"
                },
                data_text="ECG Report: Normal sinus rhythm, HR 72 bpm",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr2)
            health_records.append(hr2)
            
            # Lab report
            hr3 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="LAB_REPORT",
                record_date=datetime.now(timezone.utc) - timedelta(days=5),
                data_json={
                    "testName": "Lipid Profile",
                    "results": {
                        "totalCholesterol": "210 mg/dL",
                        "ldl": "130 mg/dL",
                        "hdl": "45 mg/dL",
                        "triglycerides": "150 mg/dL"
                    },
                    "status": "BORDERLINE_HIGH",
                    "lab": "City Diagnostics",
                    "referenceRange": "Total: <200, LDL: <100, HDL: >40, TG: <150"
                },
                data_text="Lipid profile - Total cholesterol 210 mg/dL (borderline high)",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr3)
            health_records.append(hr3)
            
            print_info(f"  Created 3 records for {patient.name}")
        
        # Priya Singh - Orthopedic records
        if len(patients) > 1:
            patient = db.query(Patient).filter_by(id=patients[1].id).first()
            
            # Prescription
            hr4 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="PRESCRIPTION",
                record_date=datetime.now(timezone.utc) - timedelta(days=3),
                data_json={
                    "medications": [
                        {
                            "name": "Ibuprofen 400mg",
                            "dosage": "1 tablet three times daily",
                            "duration": "7 days",
                            "instructions": "Take after meals"
                        },
                        {
                            "name": "Calcium + Vitamin D3",
                            "dosage": "1 tablet daily",
                            "duration": "60 days",
                            "instructions": "Take with breakfast"
                        }
                    ],
                    "doctor": "Dr. Verma (Orthopedic Surgeon)",
                    "department": "Orthopedics",
                    "diagnosis": "Post-operative care - ACL reconstruction",
                    "followUpDate": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
                },
                data_text="Post-surgery prescription for ACL reconstruction",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr4)
            health_records.append(hr4)
            
            # X-ray report
            hr5 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="DIAGNOSTIC_REPORT",
                record_date=datetime.now(timezone.utc) - timedelta(days=3),
                data_json={
                    "reportType": "X-RAY",
                    "testName": "Knee X-Ray (Post-operative)",
                    "findings": "Surgical hardware in proper position. No signs of infection or displacement. Bone healing progressing normally.",
                    "interpretation": "Satisfactory post-operative status",
                    "performedBy": "Dr. Reddy",
                    "department": "Radiology"
                },
                data_text="Post-operative knee X-ray: Hardware in proper position",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr5)
            health_records.append(hr5)
            
            print_info(f"  Created 2 records for {patient.name}")
        
        # Amit Patel - General health records
        if len(patients) > 2:
            patient = db.query(Patient).filter_by(id=patients[2].id).first()
            
            # General checkup report
            hr6 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="CONSULTATION_NOTES",
                record_date=datetime.now(timezone.utc),
                data_json={
                    "chiefComplaint": "Annual health checkup",
                    "vitals": {
                        "bloodPressure": "120/80 mmHg",
                        "pulse": "72 bpm",
                        "temperature": "98.6°F",
                        "respiratoryRate": "16 breaths/min"
                    },
                    "generalExamination": "Well-built and nourished",
                    "systemicExamination": "Within normal limits",
                    "assessment": "Healthy individual with normal parameters",
                    "plan": "Continue healthy lifestyle, annual followup"
                },
                data_text="General health checkup - All parameters normal",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr6)
            health_records.append(hr6)
            
            # Blood test
            hr7 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="LAB_REPORT",
                record_date=datetime.now(timezone.utc),
                data_json={
                    "testName": "Complete Blood Count (CBC)",
                    "results": {
                        "hemoglobin": "14.5 g/dL",
                        "wbc": "7500 cells/mcL",
                        "platelets": "250000 cells/mcL"
                    },
                    "status": "NORMAL",
                    "lab": "City Diagnostics",
                    "referenceRanges": {
                        "hemoglobin": "13.5-17.5 g/dL",
                        "wbc": "4500-11000 cells/mcL",
                        "platelets": "150000-400000 cells/mcL"
                    }
                },
                data_text="CBC Report - All values within normal range",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr7)
            health_records.append(hr7)
            
            print_info(f"  Created 2 records for {patient.name}")
        
        # Neha Sharma - Neurology records
        if len(patients) > 3:
            patient = db.query(Patient).filter_by(id=patients[3].id).first()
            
            # Consultation notes
            hr8 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="CONSULTATION_NOTES",
                record_date=datetime.now(timezone.utc) - timedelta(days=5),
                data_json={
                    "chiefComplaint": "Headache and dizziness",
                    "history": "Occasional headaches for past 3 months, triggered by stress",
                    "examination": "Neurological examination normal, no focal deficits",
                    "assessment": "Tension headache with vertigo",
                    "plan": "Lifestyle modifications, stress management, follow-up in 2 weeks"
                },
                data_text="Neurology consultation for headache and dizziness",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr8)
            health_records.append(hr8)
            
            # MRI report
            hr9 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="DIAGNOSTIC_REPORT",
                record_date=datetime.now(timezone.utc) - timedelta(days=4),
                data_json={
                    "reportType": "MRI",
                    "testName": "Brain MRI with contrast",
                    "findings": "Normal brain parenchyma. No focal lesions, mass effect or abnormal signal intensity.",
                    "interpretation": "Normal MRI brain",
                    "performedBy": "Dr. Gupta (Radiologist)",
                    "department": "Neuroradiology"
                },
                data_text="Brain MRI - Normal study, no abnormal findings",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr9)
            health_records.append(hr9)
            
            print_info(f"  Created 2 records for {patient.name}")
        
        db.commit()
        print_success(f"Created {len(health_records)} health records")
        return health_records
    
    except Exception as e:
        print_error(f"Failed to create health records: {e}")
        db.rollback()
        return []
    finally:
        db.close()

# ============================================================================
# GATEWAY AUTHENTICATION & BRIDGE MANAGEMENT
# ============================================================================

def setup_authentication() -> Optional[str]:
    """
    Authenticate with ABDM Gateway and get access token.
    Stores token in .env file.
    """
    print_section("Gateway Authentication")
    
    try:
        # Check if gateway is reachable
        response = requests.get(f"{GATEWAY_URL}/health", timeout=5)
        if response.status_code != 200:
            print_warning(f"Gateway health check failed: {response.status_code}")
            print_info("Proceeding with stored credentials (gateway might start later)")
            return None
    except requests.RequestException as e:
        print_warning(f"Cannot reach gateway at {GATEWAY_URL}: {e}")
        print_info("Will use default credentials from .env file")
        return None
    
    try:
        # Prepare authentication request
        auth_payload = {
            "clientId": DEFAULT_CLIENT_ID,
            "clientSecret": DEFAULT_CLIENT_SECRET,
            "grantType": "client_credentials"
        }
        
        headers = {
            "REQUEST-ID": str(uuid.uuid4()),
            "TIMESTAMP": datetime.now(timezone.utc).isoformat(),
            "X-CM-ID": DEFAULT_X_CM_ID,
            "Content-Type": "application/json"
        }
        
        print_info(f"Authenticating with gateway: {GATEWAY_URL}")
        response = requests.post(
            f"{GATEWAY_URL}/api/auth/session",
            json=auth_payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("accessToken")
            expires_in = data.get("expiresIn", 900)
            
            # Save token to .env
            save_env_variable("ACCESS_TOKEN", access_token)
            save_env_variable("TOKEN_EXPIRES_IN", str(expires_in))
            
            print_success(f"✓ Authentication successful")
            print_info(f"  Access Token (expires in {expires_in}s): {access_token[:20]}...")
            return access_token
        else:
            print_warning(f"Authentication failed: {response.status_code}")
            print_info(f"Response: {response.text}")
            return None
    
    except Exception as e:
        print_warning(f"Failed to authenticate with gateway: {e}")
        print_info("Will continue with local setup")
        return None

def register_bridge_with_gateway(access_token: Optional[str]) -> bool:
    """Register bridge (HIP) with ABDM Gateway"""
    print_section("Bridge Registration with Gateway")
    
    if not access_token:
        print_warning("No access token available. Skipping bridge registration.")
        print_info("Bridge will need to be registered manually after gateway is running.")
        return False
    
    try:
        bridge_payload = {
            "bridgeId": DEFAULT_BRIDGE_ID_HIP,
            "entityType": DEFAULT_ENTITY_TYPE,
            "name": HOSPITAL_NAME
        }
        
        headers = {
            "REQUEST-ID": str(uuid.uuid4()),
            "TIMESTAMP": datetime.now(timezone.utc).isoformat(),
            "X-CM-ID": DEFAULT_X_CM_ID,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        print_info(f"Registering bridge: {DEFAULT_BRIDGE_ID_HIP}")
        response = requests.post(
            f"{GATEWAY_URL}/api/bridge/register",
            json=bridge_payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"✓ Bridge registered successfully")
            print_info(f"  Bridge ID: {data.get('bridgeId')}")
            print_info(f"  Entity Type: {data.get('entityType')}")
            return True
        else:
            print_warning(f"Bridge registration failed: {response.status_code}")
            print_info(f"Response: {response.text}")
            return False
    
    except Exception as e:
        print_warning(f"Failed to register bridge: {e}")
        return False

def update_bridge_webhook(access_token: Optional[str]) -> bool:
    """Update bridge webhook URL"""
    print_section("Bridge Webhook Configuration")
    
    if not access_token:
        print_warning("No access token available. Skipping webhook update.")
        return False
    
    try:
        webhook_payload = {
            "bridgeId": DEFAULT_BRIDGE_ID_HIP,
            "webhookUrl": HOSPITAL_WEBHOOK_URL
        }
        
        headers = {
            "REQUEST-ID": str(uuid.uuid4()),
            "TIMESTAMP": datetime.now(timezone.utc).isoformat(),
            "X-CM-ID": DEFAULT_X_CM_ID,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        print_info(f"Setting webhook URL: {HOSPITAL_WEBHOOK_URL}")
        response = requests.patch(
            f"{GATEWAY_URL}/api/bridge/url",
            json=webhook_payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            print_success(f"✓ Webhook URL configured successfully")
            return True
        else:
            print_warning(f"Webhook update failed: {response.status_code}")
            print_info(f"Response: {response.text}")
            return False
    
    except Exception as e:
        print_warning(f"Failed to update webhook: {e}")
        return False

def register_bridge_services(access_token: Optional[str]) -> bool:
    """Register services for the bridge"""
    print_section("Bridge Services Registration")
    
    if not access_token:
        print_warning("No access token available. Skipping service registration.")
        return False
    
    services = [
        {
            "service_id": "health-records-1",
            "service_name": "Health Records Service",
            "service_type": "HEALTH_RECORDS",
            "description": "Service for retrieving and managing health records"
        },
        {
            "service_id": "consent-1",
            "service_name": "Consent Management Service",
            "service_type": "CONSENT",
            "description": "Service for managing patient consent"
        },
        {
            "service_id": "linking-1",
            "service_name": "Patient Linking Service",
            "service_type": "LINKING",
            "description": "Service for patient identification and linking"
        }
    ]
    
    success_count = 0
    
    for service in services:
        try:
            service_payload = {
                "bridgeId": DEFAULT_BRIDGE_ID_HIP,
                "serviceId": service["service_id"],
                "serviceName": service["service_name"],
                "serviceType": service["service_type"],
                "description": service["description"]
            }
            
            headers = {
                "REQUEST-ID": str(uuid.uuid4()),
                "TIMESTAMP": datetime.now(timezone.utc).isoformat(),
                "X-CM-ID": DEFAULT_X_CM_ID,
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            print_info(f"Registering service: {service['service_name']}")
            response = requests.post(
                f"{GATEWAY_URL}/api/bridge/service",
                json=service_payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                print_success(f"  ✓ {service['service_name']} registered")
                success_count += 1
            else:
                print_warning(f"  ✗ Failed to register {service['service_name']}: {response.status_code}")
                print_info(f"    Response: {response.text}")
        
        except Exception as e:
            print_warning(f"  ✗ Failed to register {service['service_name']}: {e}")
    
    if success_count == len(services):
        print_success(f"✓ All {len(services)} services registered successfully")
        return True
    elif success_count > 0:
        print_warning(f"Partially successful: {success_count}/{len(services)} services registered")
        return True
    else:
        print_warning("No services registered")
        return False

# ============================================================================
# CONSENT MANAGEMENT SETUP
# ============================================================================

def setup_consent_management():
    """Setup consent management defaults"""
    print_section("Consent Management Configuration")
    
    try:
        consent_config = {
            "consentExpiryDays": 365,
            "defaultConsentDuration": "12 months",
            "purposes": [
                "TREATMENT",
                "DIAGNOSIS",
                "PRESCRIPTION",
                "ROUTINE_CARE"
            ],
            "dataTypes": [
                "PRESCRIPTION",
                "DIAGNOSTIC_REPORT",
                "LAB_REPORT",
                "IMMUNIZATION",
                "CONSULTATION_NOTES"
            ]
        }
        
        # Save consent config to .env as JSON
        save_env_variable("CONSENT_CONFIG", json.dumps(consent_config))
        
        print_success("✓ Consent management configured")
        for purpose in consent_config["purposes"]:
            print_info(f"  Purpose: {purpose}")
        
        return True
    
    except Exception as e:
        print_error(f"Failed to setup consent management: {e}")
        return False

# ============================================================================
# LINKING MANAGEMENT SETUP
# ============================================================================

def setup_linking_management():
    """Setup patient linking defaults"""
    print_section("Patient Linking Configuration")
    
    try:
        linking_config = {
            "defaultLinkingMode": "ABHA",
            "supportedIdTypes": ["ABHA", "MOBILE", "AADHAAR"],
            "otpExpirySeconds": 300,
            "maxOtpRetries": 3,
            "linkingExpiryDays": 365
        }
        
        # Save linking config to .env as JSON
        save_env_variable("LINKING_CONFIG", json.dumps(linking_config))
        
        print_success("✓ Linking management configured")
        print_info(f"  Default Mode: {linking_config['defaultLinkingMode']}")
        print_info(f"  OTP Expiry: {linking_config['otpExpirySeconds']} seconds")
        
        return True
    
    except Exception as e:
        print_error(f"Failed to setup linking management: {e}")
        return False

# ============================================================================
# ENVIRONMENT FILE GENERATION
# ============================================================================

def generate_env_file():
    """Generate comprehensive .env file with all required variables"""
    print_section("Environment Configuration")
    
    try:
        # Database configuration
        save_env_variable("DATABASE_URL", "sqlite:///./abdm_hospital_1.db")
        
        # Application settings
        save_env_variable("APP_NAME", HOSPITAL_NAME)
        save_env_variable("APP_ENV", "local")
        save_env_variable("APP_HOST", "127.0.0.1")
        save_env_variable("APP_PORT", str(HOSPITAL_PORT))
        save_env_variable("LOG_LEVEL", "INFO")
        
        # Gateway configuration
        save_env_variable("GATEWAY_BASE_URL", GATEWAY_URL)
        save_env_variable("X_CM_ID", DEFAULT_X_CM_ID)
        
        # Client credentials
        save_env_variable("CLIENT_ID", DEFAULT_CLIENT_ID)
        save_env_variable("CLIENT_SECRET", DEFAULT_CLIENT_SECRET)
        
        # Bridge configuration
        save_env_variable("BRIDGE_ID_HIP", DEFAULT_BRIDGE_ID_HIP)
        save_env_variable("BRIDGE_ID_HIU", DEFAULT_BRIDGE_ID_HIU)
        save_env_variable("BRIDGE_ID", DEFAULT_BRIDGE_ID_HIP)
        save_env_variable("ENTITY_TYPE", DEFAULT_ENTITY_TYPE)
        save_env_variable("NAME", HOSPITAL_NAME)
        
        # Webhook configuration
        save_env_variable("WEBHOOK_URL", HOSPITAL_WEBHOOK_URL)
        save_env_variable("HOSPITAL_WEBHOOK_URL", HOSPITAL_WEBHOOK_URL)
        
        # JWT configuration
        jwt_secret = generate_secure_secret(32)
        save_env_variable("JWT_SECRET", jwt_secret)
        save_env_variable("GATEWAY_JWT_SECRET", jwt_secret)
        save_env_variable("JWT_ALGORITHM", "HS256")
        save_env_variable("JWT_EXPIRY_SECONDS", "900")
        
        print_success("✓ Environment file generated with all configurations")
        print_env_file()
        
        return True
    
    except Exception as e:
        print_error(f"Failed to generate environment file: {e}")
        return False

# ============================================================================
# SUMMARY REPORT
# ============================================================================

def print_summary_report():
    """Print comprehensive summary of initialization"""
    print_header("SYSTEM INITIALIZATION COMPLETE")
    
    print_section("Hospital Configuration")
    print_info(f"Hospital Name: {HOSPITAL_NAME}")
    print_info(f"Hospital URL: {HOSPITAL_URL}")
    print_info(f"Webhook URL: {HOSPITAL_WEBHOOK_URL}")
    print_info(f"Bridge ID (HIP): {DEFAULT_BRIDGE_ID_HIP}")
    print_info(f"Client ID: {DEFAULT_CLIENT_ID}")
    
    db = SessionLocal()
    
    patients_count = db.query(Patient).count()
    visits_count = db.query(Visit).count()
    contexts_count = db.query(CareContext).count()
    records_count = db.query(HealthRecord).count()
    
    print_section("Database Summary")
    print_info(f"Patients: {patients_count}")
    print_info(f"Visits: {visits_count}")
    print_info(f"Care Contexts: {contexts_count}")
    print_info(f"Health Records: {records_count}")
    
    print_section("Patient Details")
    patients = db.query(Patient).all()
    for patient in patients:
        visits = db.query(Visit).filter_by(patient_id=patient.id).count()
        contexts = db.query(CareContext).filter_by(patient_id=patient.id).count()
        records = db.query(HealthRecord).filter_by(patient_id=patient.id).count()
        print_info(f"{patient.name}")
        print_info(f"  ABHA ID: {patient.abha_id}")
        print_info(f"  Mobile: {patient.mobile}")
        print_info(f"  Visits: {visits}, Care Contexts: {contexts}, Records: {records}")
    
    db.close()
    
    print_section("Next Steps")
    print_info("1. Start the ABDM Gateway (if not running)")
    print_info("2. Start this hospital: uvicorn app.main:app --reload --port 8080")
    print_info("3. Access the hospital UI at http://localhost:8080")
    print_info("4. Test linking and consent management features")
    print_info("5. Check /docs endpoint for API documentation")
    
    print_section("Important Files")
    env_path = Path(os.path.dirname(__file__)) / ".env"
    print_info(f"Configuration: {env_path}")
    print_info(f"Database: {Path(os.path.dirname(__file__)) / 'abdm_hospital_1.db'}")
    
    print_header("Ready to Use!")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main initialization orchestrator"""
    
    print_header("ABDM Hospital 1 - Complete System Initialization")
    print_info("This script initializes the entire ABDM hospital system")
    print_info("Database, authentication, bridge management, and default data")
    
    # Step 1: Load or create .env
    load_or_create_env_file()
    
    # Step 2: Initialize database
    if not init_database():
        print_error("Database initialization failed. Aborting.")
        return False
    
    # Step 3: Seed patient data
    patients = seed_patients()
    if not patients:
        print_error("Patient seeding failed. Aborting.")
        return False
    
    # Step 4: Seed visits
    visits = seed_visits(patients)
    
    # Step 5: Seed care contexts
    care_contexts = seed_care_contexts(patients)
    
    # Step 6: Seed health records
    health_records = seed_health_records(patients)
    
    # Step 7: Generate comprehensive .env file
    if not generate_env_file():
        print_error("Environment file generation failed. Aborting.")
        return False
    
    # Step 8: Setup consent management
    setup_consent_management()
    
    # Step 9: Setup linking management
    setup_linking_management()
    
    # Step 10: Authenticate with gateway (optional)
    access_token = setup_authentication()
    
    # Step 11: Register bridge with gateway (requires token)
    if access_token:
        bridge_registered = register_bridge_with_gateway(access_token)
        webhook_updated = update_bridge_webhook(access_token)
        services_registered = register_bridge_services(access_token)
        
        if not bridge_registered:
            print_warning("Bridge registration failed. Services registration skipped.")
        elif not webhook_updated:
            print_warning("Webhook update failed. Services registration skipped.")
        elif not services_registered:
            print_warning("Services registration incomplete.")
    else:
        print_warning("Skipping gateway registration. Token not available.")
        print_info("You can register the bridge manually later using the API endpoints.")
    
    # Step 12: Print summary
    print_summary_report()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

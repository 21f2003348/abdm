#!/usr/bin/env python3
"""
Comprehensive ABDM System Initialization for Hospital 2.
Initializes database with DIFFERENT patient data set and configurations.
Run this ONCE after system setup to fully initialize hospital 2.

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
HOSPITAL_NAME = "Apollo Health - Hospital 2"
HOSPITAL_PORT = 8081
HOSPITAL_URL = f"http://localhost:{HOSPITAL_PORT}"
HOSPITAL_WEBHOOK_URL = f"{HOSPITAL_URL}/webhook"

# Default client credentials for this hospital (must exist in gateway DB)
DEFAULT_CLIENT_ID = "client-002"
DEFAULT_CLIENT_SECRET = "secret-002"

# Bridge details for HIP (Health Information Provider)
DEFAULT_BRIDGE_ID_HIP = "hip-002"
DEFAULT_BRIDGE_ID_HIU = "hiu-002"
DEFAULT_ENTITY_TYPE = "HIP"
DEFAULT_X_CM_ID = "hospital-2"

# ============================================================================
# DIFFERENT DEFAULT DATA SETS FOR HOSPITAL 2
# ============================================================================

PATIENTS_DATA = [
    {
        "name": "Vikram Singh",
        "mobile": "8765432100",
        "aadhaar": "223456789012",
        "abha_id": "vikram.singh@sbx"
    },
    {
        "name": "Anjali Gupta",
        "mobile": "8765432101",
        "aadhaar": "223456789013",
        "abha_id": "anjali.gupta@sbx"
    },
    {
        "name": "Ravi Desai",
        "mobile": "8765432102",
        "aadhaar": "223456789014",
        "abha_id": "ravi.desai@sbx"
    },
    {
        "name": "Divya Reddy",
        "mobile": "8765432103",
        "aadhaar": "223456789015",
        "abha_id": "divya.reddy@sbx"
    },
    {
        "name": "Suresh Iyer",
        "mobile": "8765432104",
        "aadhaar": "223456789016",
        "abha_id": "suresh.iyer@sbx"
    }
]

VISITS_TEMPLATE = {
    0: [  # Vikram Singh - Pediatrics
        {
            "visit_type": "OPD",
            "department": "Pediatrics",
            "doctor_id": "DR101",
            "days_offset": -14,
            "status": "Completed"
        },
        {
            "visit_type": "OPD",
            "department": "Pediatrics",
            "doctor_id": "DR101",
            "days_offset": 7,
            "status": "Scheduled"
        }
    ],
    1: [  # Anjali Gupta - Gynecology
        {
            "visit_type": "OPD",
            "department": "Gynecology",
            "doctor_id": "DR102",
            "days_offset": -2,
            "status": "Completed"
        },
        {
            "visit_type": "OPD",
            "department": "Gynecology",
            "doctor_id": "DR102",
            "days_offset": 30,
            "status": "Scheduled"
        }
    ],
    2: [  # Ravi Desai - Dermatology
        {
            "visit_type": "OPD",
            "department": "Dermatology",
            "doctor_id": "DR103",
            "days_offset": -10,
            "status": "Completed"
        }
    ],
    3: [  # Divya Reddy - ENT
        {
            "visit_type": "IPD",
            "department": "ENT",
            "doctor_id": "DR104",
            "days_offset": -5,
            "status": "Completed"
        },
        {
            "visit_type": "OPD",
            "department": "ENT",
            "doctor_id": "DR104",
            "days_offset": 2,
            "status": "In Progress"
        }
    ],
    4: [  # Suresh Iyer - Gastroenterology
        {
            "visit_type": "OPD",
            "department": "Gastroenterology",
            "doctor_id": "DR105",
            "days_offset": -8,
            "status": "Completed"
        }
    ]
}

CARE_CONTEXTS_TEMPLATE = {
    0: {
        "context_name": "Pediatric Care - 2026",
        "description": "Child health monitoring and developmental assessment"
    },
    1: {
        "context_name": "Women's Health - 2026",
        "description": "Gynecological care and reproductive health management"
    },
    2: {
        "context_name": "Dermatology Treatment - 2026",
        "description": "Skin disease diagnosis and treatment"
    },
    3: {
        "context_name": "ENT Care - 2026",
        "description": "Ear, Nose and Throat specialist care and follow-up"
    },
    4: {
        "context_name": "Gastroenterology - 2026",
        "description": "Gastrointestinal and digestive health care"
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
    """Create default patients with DIFFERENT data for Hospital 2"""
    print_section("Creating Default Patients")
    
    db = SessionLocal()
    try:
        # Check if patients already exist
        existing = db.query(Patient).count()
        if existing > 0:
            print_warning(f"Database already contains {existing} patients. Skipping patient creation.")
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
    """Create visits with DIFFERENT specialties for Hospital 2"""
    print_section("Creating Default Visits")
    
    db = SessionLocal()
    try:
        existing = db.query(Visit).count()
        if existing > 0:
            print_warning(f"Database already contains {existing} visits. Skipping visit creation.")
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
    """Create care contexts with DIFFERENT specialties"""
    print_section("Creating Care Contexts")
    
    db = SessionLocal()
    try:
        existing = db.query(CareContext).count()
        if existing > 0:
            print_warning(f"Database already contains {existing} care contexts. Skipping creation.")
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
    """Create DIFFERENT health records for Hospital 2 specialties"""
    print_section("Creating Health Records")
    
    db = SessionLocal()
    try:
        existing = db.query(HealthRecord).count()
        if existing > 0:
            print_warning(f"Database already contains {existing} health records. Skipping creation.")
            db.close()
            return db.query(HealthRecord).all()
        
        health_records = []
        
        # Vikram Singh - Pediatrics records
        if len(patients) > 0:
            patient = db.query(Patient).filter_by(id=patients[0].id).first()
            
            # Vaccination record
            hr1 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="IMMUNIZATION",
                record_date=datetime.now(timezone.utc) - timedelta(days=14),
                data_json={
                    "vaccines": [
                        {
                            "name": "DPT (Diphtheria, Pertussis, Tetanus)",
                            "dose": "3rd Dose",
                            "date": "2026-01-05",
                            "manufacturer": "Serum Institute",
                            "batchNumber": "BATCH2026001"
                        }
                    ],
                    "administeredBy": "Dr. Rajesh (Pediatrician)",
                    "nextDueDate": "2026-07-05",
                    "weight": "15.5 kg",
                    "height": "105 cm"
                },
                data_text="DPT Vaccination - 3rd Dose administered",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr1)
            health_records.append(hr1)
            
            # Pediatric consultation
            hr2 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="CONSULTATION_NOTES",
                record_date=datetime.now(timezone.utc) - timedelta(days=14),
                data_json={
                    "chiefComplaint": "Growth monitoring and development check",
                    "vitals": {
                        "weight": "15.5 kg",
                        "height": "105 cm",
                        "temperature": "98.4°F",
                        "pulse": "110 bpm"
                    },
                    "developmentalMilestones": "Age-appropriate",
                    "immunizationStatus": "Upto date",
                    "assessment": "Healthy child with normal growth and development",
                    "plan": "Continue breastfeeding, next followup at 6 months"
                },
                data_text="Pediatric check-up - Child developing normally",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr2)
            health_records.append(hr2)
            
            print_info(f"  Created 2 records for {patient.name}")
        
        # Anjali Gupta - Gynecology records
        if len(patients) > 1:
            patient = db.query(Patient).filter_by(id=patients[1].id).first()
            
            # Obstetric consultation
            hr3 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="CONSULTATION_NOTES",
                record_date=datetime.now(timezone.utc) - timedelta(days=2),
                data_json={
                    "consultationType": "Prenatal Check-up",
                    "gestationalWeek": 28,
                    "vitals": {
                        "bloodPressure": "110/70 mmHg",
                        "weight": "72 kg",
                        "temperature": "98.6°F"
                    },
                    "findings": "Normal singleton pregnancy, fundal height appropriate for dates",
                    "foetalHeartRate": "140-150 bpm",
                    "investigations": "Routine anomaly scan done, all normal",
                    "plan": "Continue prenatal vitamins, next followup in 2 weeks"
                },
                data_text="Prenatal check-up at 28 weeks - All parameters normal",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr3)
            health_records.append(hr3)
            
            # Ultrasound report
            hr4 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="DIAGNOSTIC_REPORT",
                record_date=datetime.now(timezone.utc) - timedelta(days=1),
                data_json={
                    "reportType": "Ultrasound",
                    "testName": "Obstetric Ultrasound - 2nd Trimester",
                    "findings": "Single live intrauterine pregnancy, appropriate for 28 weeks. Morphology normal. AFI adequate. Cervical length normal.",
                    "estimation": "Due Date: 2026-04-20",
                    "performedBy": "Dr. Sharma (Sonologist)",
                    "department": "Obstetrics"
                },
                data_text="Obstetric ultrasound - Normal fetus with appropriate growth",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr4)
            health_records.append(hr4)
            
            print_info(f"  Created 2 records for {patient.name}")
        
        # Ravi Desai - Dermatology records
        if len(patients) > 2:
            patient = db.query(Patient).filter_by(id=patients[2].id).first()
            
            # Dermatology consultation
            hr5 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="CONSULTATION_NOTES",
                record_date=datetime.now(timezone.utc) - timedelta(days=10),
                data_json={
                    "chiefComplaint": "Persistent acne with scarring",
                    "duration": "3 years",
                    "distribution": "Face, back and shoulders",
                    "severity": "Moderate to severe",
                    "skinType": "Oily",
                    "assessment": "Acne vulgaris with post-acne scars",
                    "plan": "Isotretinoin therapy, monthly follow-ups, strict sun protection"
                },
                data_text="Dermatology consultation for severe acne management",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr5)
            health_records.append(hr5)
            
            # Prescription
            hr6 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="PRESCRIPTION",
                record_date=datetime.now(timezone.utc) - timedelta(days=10),
                data_json={
                    "medications": [
                        {
                            "name": "Isotretinoin 20mg",
                            "dosage": "1 capsule daily",
                            "duration": "16 weeks",
                            "instructions": "Take with fatty meal, with strict contraception"
                        },
                        {
                            "name": "Moisturizer with SPF 50",
                            "dosage": "Apply twice daily",
                            "duration": "Ongoing",
                            "instructions": "Essential during isotretinoin therapy"
                        }
                    ],
                    "doctor": "Dr. Verma (Dermatologist)",
                    "warnings": "Requires monthly pregnancy tests for females of childbearing age"
                },
                data_text="Dermatology prescription for acne treatment",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr6)
            health_records.append(hr6)
            
            print_info(f"  Created 2 records for {patient.name}")
        
        # Divya Reddy - ENT records
        if len(patients) > 3:
            patient = db.query(Patient).filter_by(id=patients[3].id).first()
            
            # ENT consultation
            hr7 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="CONSULTATION_NOTES",
                record_date=datetime.now(timezone.utc) - timedelta(days=5),
                data_json={
                    "chiefComplaint": "Post-FESS (Functional Endoscopic Sinus Surgery) follow-up",
                    "surgeryDate": "2025-12-20",
                    "findings": "Nasal cavity healing well, minimal crusting, patency maintained",
                    "assessment": "Good post-operative recovery",
                    "plan": "Continue nasal saline irrigation, regular follow-ups"
                },
                data_text="ENT follow-up post sinus surgery - healing well",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr7)
            health_records.append(hr7)
            
            # ENT examination report
            hr8 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="DIAGNOSTIC_REPORT",
                record_date=datetime.now(timezone.utc) - timedelta(days=4),
                data_json={
                    "reportType": "Nasal Endoscopy",
                    "testName": "Post-operative Nasal Endoscopy",
                    "findings": "Nasal mucosa pink and healthy, no pus or polyps, patent ostium",
                    "interpretation": "Successful FESS with good post-operative status",
                    "performedBy": "Dr. Desai (ENT Specialist)",
                    "department": "ENT"
                },
                data_text="Nasal endoscopy - Post-operative cavity in good condition",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr8)
            health_records.append(hr8)
            
            print_info(f"  Created 2 records for {patient.name}")
        
        # Suresh Iyer - Gastroenterology records
        if len(patients) > 4:
            patient = db.query(Patient).filter_by(id=patients[4].id).first()
            
            # GI consultation
            hr9 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="CONSULTATION_NOTES",
                record_date=datetime.now(timezone.utc) - timedelta(days=8),
                data_json={
                    "chiefComplaint": "Chronic GERD and Dyspepsia",
                    "duration": "2 years",
                    "symptoms": "Heartburn, bloating, loss of appetite",
                    "triggers": "Spicy food, stress, late meals",
                    "assessment": "Gastroesophageal reflux disease with functional dyspepsia",
                    "plan": "Lifestyle modification, PPI therapy, endoscopy if symptoms persist"
                },
                data_text="Gastroenterology consultation for GERD management",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr9)
            health_records.append(hr9)
            
            # Endoscopy report
            hr10 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="DIAGNOSTIC_REPORT",
                record_date=datetime.now(timezone.utc) - timedelta(days=7),
                data_json={
                    "reportType": "Upper GI Endoscopy",
                    "testName": "OGD (Oesophago-Gastro-Duodenoscopy)",
                    "findings": "Mild oesophagitis in lower third, normal cardia and stomach, normal duodenum",
                    "biopsyTaken": False,
                    "interpretation": "Findings consistent with GERD",
                    "performedBy": "Dr. Kulkarni (Gastroenterologist)",
                    "department": "Gastroenterology"
                },
                data_text="Upper GI endoscopy - Evidence of reflux esophagitis",
                was_encrypted=False,
                decryption_status="NONE"
            )
            db.add(hr10)
            health_records.append(hr10)
            
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
    """Authenticate with ABDM Gateway and get access token."""
    print_section("Gateway Authentication")
    
    try:
        response = requests.get(f"{GATEWAY_URL}/health", timeout=5)
        if response.status_code != 200:
            print_warning(f"Gateway health check failed: {response.status_code}")
            return None
    except requests.RequestException as e:
        print_warning(f"Cannot reach gateway at {GATEWAY_URL}: {e}")
        return None
    
    try:
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
            
            save_env_variable("ACCESS_TOKEN", access_token)
            save_env_variable("TOKEN_EXPIRES_IN", str(expires_in))
            
            print_success(f"✓ Authentication successful")
            print_info(f"  Access Token (expires in {expires_in}s): {access_token[:20]}...")
            return access_token
        else:
            print_warning(f"Authentication failed: {response.status_code}")
            return None
    
    except Exception as e:
        print_warning(f"Failed to authenticate: {e}")
        return None

def register_bridge_with_gateway(access_token: Optional[str]) -> bool:
    """Register bridge with ABDM Gateway"""
    print_section("Bridge Registration with Gateway")
    
    if not access_token:
        print_warning("No access token. Skipping bridge registration.")
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
            print_success(f"✓ Bridge registered successfully")
            return True
        else:
            print_warning(f"Bridge registration failed: {response.status_code}")
            return False
    
    except Exception as e:
        print_warning(f"Failed to register bridge: {e}")
        return False

def update_bridge_webhook(access_token: Optional[str]) -> bool:
    """Update bridge webhook URL"""
    print_section("Bridge Webhook Configuration")
    
    if not access_token:
        print_warning("No access token. Skipping webhook update.")
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
            print_success(f"✓ Webhook configured successfully")
            return True
        else:
            print_warning(f"Webhook update failed: {response.status_code}")
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
            "service_id": "health-records-2",
            "service_name": "Health Records Service",
            "service_type": "HEALTH_RECORDS",
            "description": "Service for retrieving and managing health records"
        },
        {
            "service_id": "consent-2",
            "service_name": "Consent Management Service",
            "service_type": "CONSENT",
            "description": "Service for managing patient consent"
        },
        {
            "service_id": "linking-2",
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
# CONSENT & LINKING MANAGEMENT
# ============================================================================

def setup_consent_management():
    """Setup consent management"""
    print_section("Consent Management Configuration")
    
    try:
        consent_config = {
            "consentExpiryDays": 365,
            "defaultConsentDuration": "12 months",
            "purposes": [
                "TREATMENT",
                "DIAGNOSIS",
                "PRESCRIPTION",
                "ROUTINE_CARE",
                "RESEARCH"
            ],
            "dataTypes": [
                "PRESCRIPTION",
                "DIAGNOSTIC_REPORT",
                "LAB_REPORT",
                "IMMUNIZATION",
                "CONSULTATION_NOTES",
                "OBSTETRIC_RECORDS"
            ]
        }
        
        save_env_variable("CONSENT_CONFIG", json.dumps(consent_config))
        
        print_success("✓ Consent management configured")
        return True
    
    except Exception as e:
        print_error(f"Failed to setup consent management: {e}")
        return False

def setup_linking_management():
    """Setup patient linking"""
    print_section("Patient Linking Configuration")
    
    try:
        linking_config = {
            "defaultLinkingMode": "ABHA",
            "supportedIdTypes": ["ABHA", "MOBILE", "AADHAAR"],
            "otpExpirySeconds": 300,
            "maxOtpRetries": 3,
            "linkingExpiryDays": 365
        }
        
        save_env_variable("LINKING_CONFIG", json.dumps(linking_config))
        
        print_success("✓ Linking management configured")
        return True
    
    except Exception as e:
        print_error(f"Failed to setup linking: {e}")
        return False

# ============================================================================
# ENVIRONMENT FILE GENERATION
# ============================================================================

def generate_env_file():
    """Generate .env file for Hospital 2"""
    print_section("Environment Configuration")
    
    try:
        # Database configuration
        save_env_variable("DATABASE_URL", "sqlite:///./abdm_hospital_2.db")
        
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
        
        print_success("✓ Environment file generated")
        print_env_file()
        
        return True
    
    except Exception as e:
        print_error(f"Failed to generate environment file: {e}")
        return False

# ============================================================================
# SUMMARY REPORT
# ============================================================================

def print_summary_report():
    """Print initialization summary"""
    print_header("HOSPITAL 2 SYSTEM INITIALIZATION COMPLETE")
    
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
    print_info("2. Start this hospital: uvicorn app.main:app --reload --port 8081")
    print_info("3. Access the hospital UI at http://localhost:8081")
    print_info("4. Test linking and consent features")
    
    print_section("Important Files")
    env_path = Path(os.path.dirname(__file__)) / ".env"
    print_info(f"Configuration: {env_path}")
    print_info(f"Database: {Path(os.path.dirname(__file__)) / 'abdm_hospital_2.db'}")
    
    print_header("Hospital 2 Ready!")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main initialization orchestrator"""
    
    print_header("ABDM Hospital 2 - Complete System Initialization")
    print_info("Different patient data, specialties, and configurations")
    
    # Step 1: Load or create .env
    load_or_create_env_file()
    
    # Step 2: Initialize database
    if not init_database():
        return False
    
    # Step 3-6: Seed data
    patients = seed_patients()
    if not patients:
        return False
    
    visits = seed_visits(patients)
    care_contexts = seed_care_contexts(patients)
    health_records = seed_health_records(patients)
    
    # Step 7: Generate .env file
    if not generate_env_file():
        return False
    
    # Step 8-9: Setup management systems
    setup_consent_management()
    setup_linking_management()
    
    # Step 10-12: Gateway integration
    access_token = setup_authentication()
    
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
    
    # Step 13: Print summary
    print_summary_report()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

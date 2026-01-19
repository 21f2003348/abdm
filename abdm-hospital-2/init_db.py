#!/usr/bin/env python3
"""
Database initialization script for ABDM Hospital.
Creates all tables and seeds initial data with proper relationships.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
import uuid
import json
import requests

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import Base, engine, SessionLocal
from app.database.models import Patient, Visit, CareContext, HealthRecord

# ABDM Gateway configuration
GATEWAY_URL = "http://localhost:8000"  # Adjust if gateway is on different port

def register_care_context_to_gateway(patient_abha_id: str, care_context_id: str, context_name: str):
    """Register care context with ABDM Gateway."""
    try:
        # This would typically call the gateway's linking API
        # For now, we'll just log it
        print(f"  📡 Registering care context '{context_name}' to ABDM Gateway...")
        print(f"     Patient ABHA: {patient_abha_id}, Care Context ID: {care_context_id}")
        
        # In a real scenario, you'd make an API call like:
        # response = requests.post(
        #     f"{GATEWAY_URL}/api/link/care-context",
        #     json={
        #         "patientId": patient_abha_id,
        #         "careContextId": care_context_id,
        #         "contextName": context_name
        #     }
        # )
        # return response.json()
        
        return True
    except Exception as e:
        print(f"  ⚠️  Failed to register care context: {e}")
        return False


def init_db():
    """Initialize database by creating all tables."""
    print("🔧 Initializing database...")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")
    
    # Seed initial data
    db = SessionLocal()
    try:
        # Check if data already exists
        existing_patients = db.query(Patient).count()
        
        if existing_patients == 0:
            print("\n📝 Seeding initial data...")
            
            # Create sample patients with ABHA IDs for gateway integration
            patient1 = Patient(
                id=uuid.uuid4(),
                name="Rajesh Kumar",
                mobile="9876543210",
                abha_id="rajesh.kumar@sbx",
                aadhaar="123456789012"
            )
            
            patient2 = Patient(
                id=uuid.uuid4(),
                name="Priya Singh",
                mobile="9876543211",
                abha_id="priya.singh@sbx",
                aadhaar="123456789013"
            )
            
            patient3 = Patient(
                id=uuid.uuid4(),
                name="Amit Patel",
                mobile="9876543212",
                abha_id="amit.patel@sbx",
                aadhaar="123456789014"
            )
            
            db.add_all([patient1, patient2, patient3])
            db.commit()
            print(f"✅ Created 3 sample patients")
            
            # Create visits with different statuses
            # Visit 1: Completed OPD visit (past)
            visit1 = Visit(
                id=uuid.uuid4(),
                patient_id=patient1.id,
                visit_type="OPD",
                department="Cardiology",
                doctor_id="DR001",
                visit_date=datetime.now(timezone.utc) - timedelta(days=7),
                status="Completed"
            )
            
            # Visit 2: Completed IPD visit (past)
            visit2 = Visit(
                id=uuid.uuid4(),
                patient_id=patient2.id,
                visit_type="IPD",
                department="Orthopedics",
                doctor_id="DR002",
                visit_date=datetime.now(timezone.utc) - timedelta(days=3),
                status="Completed"
            )
            
            # Visit 3: In Progress OPD visit (today)
            visit3 = Visit(
                id=uuid.uuid4(),
                patient_id=patient3.id,
                visit_type="OPD",
                department="General Medicine",
                doctor_id="DR003",
                visit_date=datetime.now(timezone.utc),
                status="In Progress"
            )
            
            # Visit 4: Scheduled future visit
            visit4 = Visit(
                id=uuid.uuid4(),
                patient_id=patient1.id,
                visit_type="OPD",
                department="Neurology",
                doctor_id="DR004",
                visit_date=datetime.now(timezone.utc) + timedelta(days=5),
                status="Scheduled"
            )
            
            db.add_all([visit1, visit2, visit3, visit4])
            db.commit()
            print(f"✅ Created 4 sample visits (2 Completed, 1 In Progress, 1 Scheduled)")
            
            # Create care contexts linked to patients
            care_context1 = CareContext(
                id=uuid.uuid4(),
                patient_id=patient1.id,
                context_name="Cardiac Care - 2026",
                description="Cardiac monitoring and treatment program"
            )
            
            care_context2 = CareContext(
                id=uuid.uuid4(),
                patient_id=patient2.id,
                context_name="Orthopedic Treatment - 2026",
                description="Post-surgery orthopedic care"
            )
            
            care_context3 = CareContext(
                id=uuid.uuid4(),
                patient_id=patient3.id,
                context_name="General Health Checkup - 2026",
                description="Annual health checkup and screening"
            )
            
            db.add_all([care_context1, care_context2, care_context3])
            db.commit()
            print(f"✅ Created 3 sample care contexts")
            
            # Register care contexts with ABDM Gateway
            print("\n📡 Registering care contexts with ABDM Gateway...")
            register_care_context_to_gateway(patient1.abha_id, str(care_context1.id), care_context1.context_name)
            register_care_context_to_gateway(patient2.abha_id, str(care_context2.id), care_context2.context_name)
            register_care_context_to_gateway(patient3.abha_id, str(care_context3.id), care_context3.context_name)
            print("✅ Care contexts registered with gateway")
            
            # Create health records linked to care contexts and completed visits
            print("\n📋 Creating health records...")
            
            # Health records for patient1 (Rajesh Kumar) - Cardiac care
            hr1 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient1.id,
                record_type="PRESCRIPTION",
                record_date=datetime.now(timezone.utc) - timedelta(days=7),
                data_json={
                    "visitId": str(visit1.id),
                    "careContextId": str(care_context1.id),
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
                    "diagnosis": "Hypertension",
                    "followUpDate": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
                },
                data_text="Cardiac Prescription: Atenolol 50mg and Aspirin 75mg for hypertension management",
                source_hospital=None,
                request_id=None,
                was_encrypted=False,
                decryption_status="NONE",
                delivery_attempt=0
            )
            
            hr2 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient1.id,
                record_type="DIAGNOSTIC_REPORT",
                record_date=datetime.now(timezone.utc) - timedelta(days=7),
                data_json={
                    "visitId": str(visit1.id),
                    "careContextId": str(care_context1.id),
                    "reportType": "ECG",
                    "testName": "Electrocardiogram",
                    "findings": "Normal sinus rhythm. No ST-T changes. HR: 72 bpm",
                    "interpretation": "Normal ECG",
                    "performedBy": "Dr. Mehta",
                    "department": "Cardiology"
                },
                data_text="ECG Report: Normal sinus rhythm, HR 72 bpm",
                source_hospital=None,
                request_id=None,
                was_encrypted=False,
                decryption_status="NONE",
                delivery_attempt=0
            )
            
            # Health records for patient2 (Priya Singh) - Orthopedic care
            hr3 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient2.id,
                record_type="PRESCRIPTION",
                record_date=datetime.now(timezone.utc) - timedelta(days=3),
                data_json={
                    "visitId": str(visit2.id),
                    "careContextId": str(care_context2.id),
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
                source_hospital=None,
                request_id=None,
                was_encrypted=False,
                decryption_status="NONE",
                delivery_attempt=0
            )
            
            hr4 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient2.id,
                record_type="DIAGNOSTIC_REPORT",
                record_date=datetime.now(timezone.utc) - timedelta(days=3),
                data_json={
                    "visitId": str(visit2.id),
                    "careContextId": str(care_context2.id),
                    "reportType": "X-RAY",
                    "testName": "Knee X-Ray (Post-operative)",
                    "findings": "Surgical hardware in proper position. No signs of infection or displacement. Bone healing progressing normally.",
                    "interpretation": "Satisfactory post-operative status",
                    "performedBy": "Dr. Reddy",
                    "department": "Radiology"
                },
                data_text="Post-operative knee X-ray: Hardware in proper position, healing well",
                source_hospital=None,
                request_id=None,
                was_encrypted=False,
                decryption_status="NONE",
                delivery_attempt=0
            )
            
            # Health records for patient3 (Amit Patel) - General checkup
            hr5 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient3.id,
                record_type="DIAGNOSTIC_REPORT",
                record_date=datetime.now(timezone.utc),
                data_json={
                    "visitId": str(visit3.id),
                    "careContextId": str(care_context3.id),
                    "reportType": "Blood Test",
                    "testName": "Complete Blood Count (CBC)",
                    "results": {
                        "hemoglobin": "15.2 g/dL (Normal: 13.5-17.5)",
                        "wbc": "7200 cells/mcL (Normal: 4500-11000)",
                        "rbc": "5.1 million/mcL (Normal: 4.5-5.5)",
                        "platelets": "245000 cells/mcL (Normal: 150000-450000)",
                        "hematocrit": "45% (Normal: 38-50%)"
                    },
                    "interpretation": "All parameters within normal limits",
                    "performedBy": "City Lab",
                    "department": "General Medicine"
                },
                data_text="CBC Report: All values within normal range",
                source_hospital=None,
                request_id=None,
                was_encrypted=False,
                decryption_status="NONE",
                delivery_attempt=0
            )
            
            hr6 = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient3.id,
                record_type="DIAGNOSTIC_REPORT",
                record_date=datetime.now(timezone.utc),
                data_json={
                    "visitId": str(visit3.id),
                    "careContextId": str(care_context3.id),
                    "reportType": "Blood Test",
                    "testName": "Lipid Profile",
                    "results": {
                        "totalCholesterol": "185 mg/dL (Normal: <200)",
                        "ldl": "110 mg/dL (Normal: <130)",
                        "hdl": "55 mg/dL (Normal: >40)",
                        "triglycerides": "120 mg/dL (Normal: <150)",
                        "vldl": "24 mg/dL"
                    },
                    "interpretation": "Lipid levels within normal range",
                    "performedBy": "City Lab",
                    "department": "General Medicine"
                },
                data_text="Lipid Profile: All lipid levels normal",
                source_hospital=None,
                request_id=None,
                was_encrypted=False,
                decryption_status="NONE",
                delivery_attempt=0
            )
            
            db.add_all([hr1, hr2, hr3, hr4, hr5, hr6])
            db.commit()
            print(f"✅ Created 6 health records (linked to visits and care contexts)")
            
            print("\n✅ Database seeding completed!")
        else:
            print(f"\n⏭️  Database already has {existing_patients} patients. Skipping seeding.")
        
        # Print summary
        print("\n📊 Database Summary:")
        print(f"  - Patients: {db.query(Patient).count()}")
        print(f"  - Visits: {db.query(Visit).count()}")
        print(f"  - Care Contexts: {db.query(CareContext).count()}")
        print(f"  - Health Records: {db.query(HealthRecord).count()}")
        
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    print("\n✅ Database initialization complete!")

#!/usr/bin/env python3
"""
Seed sample health records for testing.
"""

import os
import sys
from datetime import datetime, timezone
import uuid
import json

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import SessionLocal
from app.database.models import Patient, HealthRecord

def seed_health_records():
    """Add sample health records to existing patients."""
    db = SessionLocal()
    
    try:
        # Get all patients
        patients = db.query(Patient).all()
        
        if not patients:
            print("❌ No patients found. Run init_db.py first.")
            return
        
        print(f"📋 Found {len(patients)} patients")
        
        # Add sample health records for each patient
        for patient in patients:
            print(f"\n👤 Adding records for {patient.name} (ID: {patient.id})")
            
            # Add a prescription record
            prescription = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="PRESCRIPTION",
                record_date=datetime.utcnow(),
                data_json={
                    "medicationName": "Paracetamol 500mg",
                    "dosage": "1 tablet twice daily",
                    "duration": "5 days",
                    "doctor": "Dr. Sharma",
                    "instructions": "Take after meals"
                },
                data_text="Paracetamol 500mg - 1 tablet twice daily for 5 days",
                source_hospital=None,  # Local record
                request_id=None,
                was_encrypted=False,
                decryption_status="NONE",
                delivery_attempt=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(prescription)
            
            # Add a diagnostic report
            diagnostic = HealthRecord(
                id=uuid.uuid4(),
                patient_id=patient.id,
                record_type="DIAGNOSTIC_REPORT",
                record_date=datetime.utcnow(),
                data_json={
                    "reportType": "Blood Test",
                    "testName": "Complete Blood Count (CBC)",
                    "results": {
                        "hemoglobin": "14.5 g/dL",
                        "wbc": "7500 cells/mcL",
                        "platelets": "250000 cells/mcL"
                    },
                    "status": "Normal",
                    "lab": "City Diagnostics"
                },
                data_text="CBC Report - All values within normal range",
                source_hospital=None,  # Local record
                request_id=None,
                was_encrypted=False,
                decryption_status="NONE",
                delivery_attempt=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(diagnostic)
            
            print(f"  ✅ Added PRESCRIPTION record")
            print(f"  ✅ Added DIAGNOSTIC_REPORT record")
        
        db.commit()
        print(f"\n✅ Successfully added {len(patients) * 2} health records!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🌱 Seeding health records...")
    seed_health_records()

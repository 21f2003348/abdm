"""
Encryption utility for ABDM Hospital.
Decrypts health data received from the gateway.

Uses the same Fernet cipher as the gateway with shared JWT_SECRET.
"""

import os
import base64
import hashlib
from cryptography.fernet import Fernet
from typing import Dict, Any
import json

class DataDecryption:
    """
    Decrypt health data received from ABDM Gateway.
    Uses shared JWT_SECRET to derive encryption key.
    """
    
    def __init__(self, jwt_secret: str = None):
        """
        Initialize with JWT secret.
        
        Args:
            jwt_secret: Shared secret with gateway (from GATEWAY_JWT_SECRET env var)
        """
        self.jwt_secret = jwt_secret or os.getenv("GATEWAY_JWT_SECRET", "dev-secret-123")
        self.cipher = self._create_cipher()
    
    def _create_cipher(self) -> Fernet:
        """
        Create Fernet cipher from JWT secret.
        Uses SHA-256 hash of secret as key material, base64 encoded.
        
        This matches the gateway's encryption setup.
        
        Returns:
            Fernet cipher instance
        """
        # Hash the secret to get consistent key material
        hashed_secret = hashlib.sha256(self.jwt_secret.encode()).digest()
        # Base64 encode for Fernet (requires 32 bytes base64-encoded)
        key = base64.urlsafe_b64encode(hashed_secret)
        return Fernet(key)
    
    def decrypt_string(self, encrypted_data: str) -> str:
        """
        Decrypt an encrypted string.
        
        Args:
            encrypted_data: Base64-encoded encrypted string from gateway
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            ValueError: If decryption fails
        """
        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_data.encode())
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to decrypt data: {str(e)}")
    
    def decrypt_json(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt encrypted JSON data.
        
        Args:
            encrypted_data: Base64-encoded encrypted JSON from gateway
            
        Returns:
            Decrypted dictionary
            
        Raises:
            ValueError: If decryption or JSON parsing fails
        """
        try:
            decrypted_string = self.decrypt_string(encrypted_data)
            return json.loads(decrypted_string)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse decrypted JSON: {str(e)}")
    
    def decrypt_health_records(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt health records from gateway response.
        
        Expected decrypted format:
        {
            "patientId": "...",
            "records": [...],
            "metadata": {...},
            "receivedAt": "..."
        }
        
        Args:
            encrypted_data: Encrypted health data from gateway
            
        Returns:
            Dictionary with patientId, records, metadata, and receivedAt
            
        Raises:
            ValueError: If decryption fails
        """
        return self.decrypt_json(encrypted_data)
    
    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt a generic encrypted dictionary.
        
        Args:
            encrypted_data: Base64-encoded encrypted dictionary
            
        Returns:
            Decrypted dictionary
        """
        return self.decrypt_json(encrypted_data)


# Module-level convenience functions
_decryption = None

def get_decryption_engine(jwt_secret: str = None) -> DataDecryption:
    """
    Get or create a DataDecryption engine.
    
    Args:
        jwt_secret: JWT secret (uses env var if not provided)
        
    Returns:
        DataDecryption instance
    """
    global _decryption
    if _decryption is None:
        _decryption = DataDecryption(jwt_secret)
    return _decryption

def decrypt_health_data(encrypted_data: str, jwt_secret: str = None) -> Dict[str, Any]:
    """
    Decrypt health data received from gateway.
    
    Args:
        encrypted_data: Encrypted data from gateway webhook
        jwt_secret: Optional JWT secret (uses env var if not provided)
        
    Returns:
        Decrypted health data dictionary
    """
    engine = get_decryption_engine(jwt_secret)
    return engine.decrypt_health_records(encrypted_data)

def decrypt_string(encrypted_data: str, jwt_secret: str = None) -> str:
    """
    Decrypt a generic encrypted string.
    
    Args:
        encrypted_data: Encrypted string
        jwt_secret: Optional JWT secret
        
    Returns:
        Decrypted plaintext
    """
    engine = get_decryption_engine(jwt_secret)
    return engine.decrypt_string(encrypted_data)

def decrypt_json(encrypted_data: str, jwt_secret: str = None) -> Dict[str, Any]:
    """
    Decrypt encrypted JSON data.
    
    Args:
        encrypted_data: Encrypted JSON
        jwt_secret: Optional JWT secret
        
    Returns:
        Decrypted dictionary
    """
    engine = get_decryption_engine(jwt_secret)
    return engine.decrypt_json(encrypted_data)

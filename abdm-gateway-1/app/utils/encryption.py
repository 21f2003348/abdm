"""
Encryption utilities for secure temporary data storage.
"""
from cryptography.fernet import Fernet
import base64
import hashlib
import os


class DataEncryption:
    """Handle encryption/decryption of sensitive health data."""
    
    def __init__(self):
        # Generate key from JWT_SECRET for consistency
        # In production, use a separate ENCRYPTION_KEY
        jwt_secret = os.getenv("JWT_SECRET", "secret-key-change-in-production")
        key_material = jwt_secret.encode()
        # Derive a 32-byte key using SHA256
        key_hash = hashlib.sha256(key_material).digest()
        # Fernet requires base64-encoded 32-byte key
        self.key = base64.urlsafe_b64encode(key_hash)
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt data and return base64-encoded encrypted string.
        
        Args:
            data: Plain text data to encrypt
            
        Returns:
            Encrypted data as base64 string
        """
        if not data:
            return ""
        
        encrypted_bytes = self.cipher.encrypt(data.encode())
        return encrypted_bytes.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt base64-encoded encrypted data.
        
        Args:
            encrypted_data: Encrypted data as base64 string
            
        Returns:
            Decrypted plain text data
        """
        if not encrypted_data:
            return ""
        
        decrypted_bytes = self.cipher.decrypt(encrypted_data.encode())
        return decrypted_bytes.decode()
    
    def encrypt_dict(self, data: dict) -> str:
        """
        Encrypt a dictionary by converting to JSON string.
        
        Args:
            data: Dictionary to encrypt
            
        Returns:
            Encrypted JSON as base64 string
        """
        import json
        json_str = json.dumps(data)
        return self.encrypt(json_str)
    
    def decrypt_dict(self, encrypted_data: str) -> dict:
        """
        Decrypt and parse JSON dictionary.
        
        Args:
            encrypted_data: Encrypted JSON as base64 string
            
        Returns:
            Decrypted dictionary
        """
        import json
        json_str = self.decrypt(encrypted_data)
        return json.loads(json_str) if json_str else {}


# Singleton instance
encryptor = DataEncryption()

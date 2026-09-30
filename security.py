"""Módulo de seguridad: cifrado de campos sensibles y hash de contraseñas."""
import os
import bcrypt
from cryptography.fernet import Fernet
from typing import Optional

from config import ENCRYPTION_KEY


_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = ENCRYPTION_KEY
        if not key:
            # Clave de prueba determinista para tests (32 bytes base64)
            key = "dGVzdC1rZXktZm9yLXVuaXQtdGVzdHMtMzItYnl0ZXM="
        _fernet = Fernet(key.encode())
    return _fernet


def encrypt_field(value: str) -> str:
    """Cifra un campo sensible (nombre, username) y retorna base64 string."""
    if not value:
        return ""
    f = _get_fernet()
    return f.encrypt(value.encode()).decode()


def decrypt_field(encrypted: str) -> str:
    """Descifra un campo sensible."""
    if not encrypted:
        return ""
    f = _get_fernet()
    try:
        return f.decrypt(encrypted.encode()).decode()
    except Exception:
        return ""


def hash_password(password: str) -> str:
    """Hashea contraseña con bcrypt (incluye salt). Retorna string UTF-8."""
    if not password:
        raise ValueError("Contraseña vacía")
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica contraseña contra hash bcrypt."""
    if not password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except Exception:
        return False


def generate_encryption_key() -> str:
    """Genera una clave Fernet nueva (para configurar ENCRYPTION_KEY en .env)."""
    return Fernet.generate_key().decode()


# Utilidades para compatibilidad con DB existente
def migrate_encrypt_existing(field: str) -> str:
    """Cifra un campo existente si no está ya cifrado (heurística: no es base64 válido de Fernet)."""
    if not field:
        return ""
    try:
        _get_fernet().decrypt(field.encode())
        return field  # ya cifrado
    except Exception:
        return encrypt_field(field)
#!/usr/bin/env python3
"""
Seguridad para callbacks de Telegram usando HMAC.
Previene manipulación de callback_data por usuarios maliciosos.
"""
import hmac
import hashlib
import config


# Longitud de la firma (bytes * 2 para hex)
SIGNATURE_LENGTH = 16


def generar_callback_token(user_id: int, action: str) -> str:
    """
    Genera un token HMAC firmado para callback_data.
    
    Formato: {action}_{user_id}_{signature}
    
    Args:
        user_id: ID del usuario objetivo
        action: Acción a realizar (ej: 'aprobar', 'rechazar', 'eliminar_usuario', etc.)
    
    Returns:
        String firmado: "aprobar_123456_abcdef1234567890"
    """
    payload = f"{action}_{user_id}"
    signature = hmac.new(
        config.BOT_TOKEN.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()[:SIGNATURE_LENGTH]
    return f"{payload}_{signature}"


def validar_callback_token(data: str, expected_action: str) -> int | None:
    """
    Valida un callback_data firmado con HMAC.
    
    Args:
        data: callback_data recibido (ej: "aprobar_123456_abcdef1234567890")
        expected_action: Acción esperada (ej: "aprobar")
    
    Returns:
        user_id si es válido, None si es inválido o manipulado
    """
    if not data:
        return None
    
    # Separar payload y firma (último _ separa la firma)
    parts = data.rsplit("_", 1)
    if len(parts) != 2:
        return None
    
    payload, signature = parts
    
    # Verificar que la acción coincide
    expected_prefix = f"{expected_action}_"
    if not payload.startswith(expected_prefix):
        return None
    
    # Extraer user_id del payload
    try:
        user_id = int(payload[len(expected_prefix):])
    except ValueError:
        return None
    
    # Verificar firma HMAC
    expected_signature = hmac.new(
        config.BOT_TOKEN.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()[:16]
    
    if not hmac.compare_digest(signature, expected_signature):
        return None
    
    return user_id


def generar_callback_token_simple(action: str, user_id: int) -> str:
    """Alias para compatibilidad: generar_callback_token(user_id, action)"""
    return generar_callback_token(user_id, action)


# Mapeo de acciones a sus prefijos para validación
CALLBACK_ACTIONS = {
    "aprobar": "aprobar",
    "rechazar": "rechazar",
    "eliminar_usuario": "eliminar_usuario",
    "ver_user": "ver_user",
    "cambiar_estado": "cambiar_estado",
    "cambiar_rol": "cambiar_rol",
    "agregar_usuario": "agregar_usuario",
}


def validar_callback_generico(data: str) -> tuple[str, int] | None:
    """
    Valida cualquier callback firmado y retorna (action, user_id).
    Retorna None si es inválido.
    """
    for action in CALLBACK_ACTIONS.values():
        user_id = validar_callback_token(data, action)
        if user_id is not None:
            return action, user_id
    return None
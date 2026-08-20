#!/bin/bash
# Script de reintento para crear la instancia ARM Always Free
# Uso: bash crear_vm_arm.sh

set -e

# Usar el root compartment (tenancy)
COMPARTMENT_ID="$OCI_TENANCY"
echo "Compartment: $COMPARTMENT_ID"

# Buscar subnet
SUBNET_ID=$(oci network subnet list --compartment-id "$COMPARTMENT_ID" --query "data[?\"display-name\"=='inventario-subnet'].id" --raw-output)
echo "Subnet: $SUBNET_ID"

# Availability domain
AD=$(oci iam availability-domain list --compartment-id "$COMPARTMENT_ID" --query "data[0].name" --raw-output)
echo "Availability Domain: $AD"

# Clave SSH
SSH_PUB="$HOME/.ssh/id_ed25519.pub"
if [ ! -f "$SSH_PUB" ]; then
    echo "Generando clave SSH..."
    ssh-keygen -t ed25519 -C "oracle-bot" -N "" -f "$HOME/.ssh/id_ed25519"
fi
SSH_KEY=$(cat "$SSH_PUB")
echo "SSH key cargada"

# Imagen Ubuntu
IMAGE_ID=$(oci compute image list --compartment-id "$COMPARTMENT_ID" --operating-system "Canonical Ubuntu" --operating-system-version "22.04" --shape "VM.Standard.A1.Flex" --query "data[0].id" --raw-output)
if [ -z "$IMAGE_ID" ] || [ "$IMAGE_ID" = "null" ]; then
    IMAGE_ID=$(oci compute image list --compartment-id "$COMPARTMENT_ID" --operating-system "Canonical Ubuntu" --operating-system-version "22.04" --query "data[?contains(\"display-name\",'aarch64')].id | [0]" --raw-output)
fi
echo "Imagen: $IMAGE_ID"

echo ""
echo "=== Intentando crear la instancia (reintentando cada 60s)... ==="
echo "Presiona Ctrl+C para detener."
echo ""

ATTEMPT=0
while true; do
    ATTEMPT=$((ATTEMPT + 1))
    echo "[Intento $ATTEMPT] $(date '+%H:%M:%S') Intentando crear VM.Standard.A1.Flex (2 OCPU / 12 GB)..."

    RESULT=$(oci compute instance launch \
        --compartment-id "$COMPARTMENT_ID" \
        --availability-domain "$AD" \
        --display-name "inventario-bot" \
        --shape "VM.Standard.A1.Flex" \
        --shape-config '{"ocpus": 2, "memoryInGBs": 12}' \
        --subnet-id "$SUBNET_ID" \
        --image-id "$IMAGE_ID" \
        --metadata "{\"ssh_authorized_keys\": \"$SSH_KEY\"}" \
        --assign-public-ip true 2>&1 || true)

    if echo "$RESULT" | grep -q '"lifecycle-state": "PROVISIONING"\|"lifecycle-state": "RUNNING"'; then
        echo ""
        echo "=============================================="
        echo " INSTANCIA CREADA EXITOSAMENTE"
        echo "=============================================="
        echo "$RESULT" | grep -E 'display-name|id' | head -5
        break
    fi

    if echo "$RESULT" | grep -q "Out of capacity\|OutOfCapacity\|500\|429"; then
        echo "   Sin capacidad, reintentando en 60s..."
    else
        echo "   Error: $(echo "$RESULT" | head -3)"
        echo "   Reintentando en 60s..."
    fi

    sleep 60
done
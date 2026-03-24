#!/usr/bin/env bash
set -euo pipefail

# One-time bootstrap: create remote state storage for Terraform.
# Run this once before `terraform init`.

RESOURCE_GROUP="househelper-tfstate-rg"
STORAGE_ACCOUNT="househelpertfstate"
CONTAINER="tfstate"
LOCATION="${1:-francecentral}"

echo "==> Creating resource group: ${RESOURCE_GROUP} in ${LOCATION}"
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}"

echo "==> Creating storage account: ${STORAGE_ACCOUNT}"
az storage account create \
  --name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --sku Standard_LRS \
  --min-tls-version TLS1_2 \
  --allow-blob-public-access false

echo "==> Creating blob container: ${CONTAINER}"
az storage container create \
  --name "${CONTAINER}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --auth-mode login

echo ""
echo "Bootstrap complete."
echo ""
echo "Next steps:"
echo "  1. Copy terraform.tfvars.example -> terraform.tfvars and fill in your subscription_id"
echo "  2. cd infra/"
echo "  3. terraform init"
echo "  4. terraform plan -var-file=terraform.tfvars"
echo "  5. terraform apply -var-file=terraform.tfvars"

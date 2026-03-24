#!/usr/bin/env bash
set -euo pipefail

# Bootstrap Terraform remote state storage.
# Safe to run multiple times — skips resources that already exist.
# Run once before `terraform init`.
#
# Usage:
#   ./bootstrap.sh                         # defaults: westeurope, new storage account
#   ./bootstrap.sh westeurope              # explicit location
#   ./bootstrap.sh westeurope myaccount    # reuse an existing storage account

LOCATION="${1:-westeurope}"
EXISTING_STORAGE="${2:-}"   # optional: name of an already-existing storage account

RESOURCE_GROUP="rg-househelper-tfstate"
CONTAINER="tfstate"

# If reusing an existing storage account, look up its resource group and skip creation.
if [[ -n "${EXISTING_STORAGE}" ]]; then
  STORAGE_ACCOUNT="${EXISTING_STORAGE}"
  echo "==> Reusing existing storage account: ${STORAGE_ACCOUNT}"

  # Verify the account exists before proceeding.
  if ! az storage account show --name "${STORAGE_ACCOUNT}" &>/dev/null; then
    echo "ERROR: Storage account '${STORAGE_ACCOUNT}' not found. Check the name and your active subscription."
    exit 1
  fi

  # Use the existing account's resource group (may differ from the tfstate RG).
  RESOURCE_GROUP=$(az storage account show \
    --name "${STORAGE_ACCOUNT}" \
    --query resourceGroup \
    --output tsv)
  echo "    Resource group: ${RESOURCE_GROUP}"
else
  STORAGE_ACCOUNT="sthousehelpertfstate"

  # Create resource group if it doesn't exist.
  if az group show --name "${RESOURCE_GROUP}" &>/dev/null; then
    echo "==> Resource group '${RESOURCE_GROUP}' already exists — skipping."
  else
    echo "==> Creating resource group: ${RESOURCE_GROUP} in ${LOCATION}"
    az group create \
      --name "${RESOURCE_GROUP}" \
      --location "${LOCATION}"
  fi

  # Create storage account if it doesn't exist.
  if az storage account show --name "${STORAGE_ACCOUNT}" --resource-group "${RESOURCE_GROUP}" &>/dev/null; then
    echo "==> Storage account '${STORAGE_ACCOUNT}' already exists — skipping."
  else
    echo "==> Creating storage account: ${STORAGE_ACCOUNT}"
    az storage account create \
      --name "${STORAGE_ACCOUNT}" \
      --resource-group "${RESOURCE_GROUP}" \
      --location "${LOCATION}" \
      --sku Standard_LRS \
      --min-tls-version TLS1_2 \
      --allow-blob-public-access false
  fi
fi

# Create the tfstate container if it doesn't exist.
if az storage container show \
    --name "${CONTAINER}" \
    --account-name "${STORAGE_ACCOUNT}" \
    --auth-mode login &>/dev/null; then
  echo "==> Container '${CONTAINER}' already exists — skipping."
else
  echo "==> Creating blob container: ${CONTAINER}"
  az storage container create \
    --name "${CONTAINER}" \
    --account-name "${STORAGE_ACCOUNT}" \
    --auth-mode login
fi

echo ""
echo "Bootstrap complete."
echo "  Resource group:   ${RESOURCE_GROUP}"
echo "  Storage account:  ${STORAGE_ACCOUNT}"
echo "  Container:        ${CONTAINER}"
echo ""
echo "Next steps:"
echo "  1. Copy terraform.tfvars.example -> terraform.tfvars and fill in your subscription_id"
echo "  2. terraform init"
echo "  3. terraform plan -var-file=terraform.tfvars"
echo "  4. terraform apply -var-file=terraform.tfvars"

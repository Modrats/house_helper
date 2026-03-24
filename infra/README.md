# Infra — Terraform IaC

Provisions the Azure infrastructure for House Helper using Terraform.

**Resources:** Container Apps (backend), Static Web Apps (frontend), Container Registry, Storage Account, Log Analytics.

---

## Prerequisites

- [`az` CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) — authenticated via `az login`
- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.7
- Contributor access to your Azure subscription

---

## First-time setup

Run once to create (or reuse) the remote state storage account:

```bash
cd infra/

# Option A — create a new dedicated state storage account (default)
./bootstrap.sh

# Option B — reuse an existing storage account
./bootstrap.sh westeurope my-existing-storage-account
```

The script is idempotent — safe to re-run. It skips resources that already exist.

Then initialise Terraform (pulls providers, configures remote backend):

```bash
terraform init
```

---

## Deploy

```bash
# Copy and fill in your subscription_id
cp terraform.tfvars.example terraform.tfvars

# Preview changes
terraform plan -var-file=terraform.tfvars

# Apply
terraform apply -var-file=terraform.tfvars
```

---

## Outputs

After a successful `apply`:

| Output | Description |
|--------|-------------|
| `backend_url` | Backend API FQDN (Container App) |
| `frontend_url` | Frontend hostname (Static Web App) |
| `acr_login_server` | ACR server for `docker push` |
| `storage_account_name` | Storage account name for app data |

---

## CI

`terraform validate` runs in CI on every push/PR to confirm the configuration is syntactically valid.

# IaC Plan — Issue #48 (Minimal Scope)
**Scope:** Backend → Container Apps | Frontend → Static Web Apps
**Complexity:** Start simple. Add resources as needed.

---

## Directory Structure

```
infra/
├── README.md
├── main.tf          # all resources in one file to start
├── variables.tf
├── outputs.tf
├── terraform.tfvars.example
└── bootstrap.sh     # one-time: create storage account for remote state
```

No modules directory. One flat `main.tf` with all resources.

---

## Azure Resources — Only These 6

| # | Resource | Purpose |
|---|----------|---------|
| 1 | `azurerm_resource_group` | One resource group for everything |
| 2 | `azurerm_container_registry` | Stores backend Docker image |
| 3 | `azurerm_container_app_environment` | Hosting environment for Container Apps |
| 4 | `azurerm_container_app` | Runs the backend FastAPI app |
| 5 | `azurerm_storage_account` | Blob + Table storage the app already uses |
| 6 | `azurerm_static_web_app` | Hosts the React frontend |

That's it. Not 15.

---

## Remote State

`bootstrap.sh` — run once manually before `terraform init`:

```bash
#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="househelper-tfstate-rg"
STORAGE_ACCOUNT="househelpertfstate"
CONTAINER="tfstate"
LOCATION="${1:-francecentral}"

az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --min-tls-version TLS1_2
az storage container create \
  --name "$CONTAINER" \
  --account-name "$STORAGE_ACCOUNT"

echo "Bootstrap done. Now run: terraform init"
```

Remote backend block in `main.tf`:

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "househelper-tfstate-rg"
    storage_account_name = "househelpertfstate"
    container_name       = "tfstate"
    key                  = "dev.terraform.tfstate"
  }
}
```

---

## Secrets

ACR credentials are passed to the Container App as secrets sourced from Terraform outputs:

```hcl
secret {
  name  = "acr-password"
  value = azurerm_container_registry.main.admin_password
}
```

> **Note:** Key Vault integration is deferred. No Key Vault to start — that's complexity for later.

---

## `terraform.tfvars.example`

```hcl
subscription_id = "00000000-0000-0000-0000-000000000000"  # Visual Studio Enterprise Subscription
location        = "francecentral"
app_prefix      = "househelper"
environment     = "dev"
```

Start with one environment (dev). Staging/prod come later.

---

## CI — `terraform validate`

Add one step to `.github/workflows/ci.yml`:

```yaml
- name: Terraform validate
  working-directory: infra
  run: |
    terraform init -backend=false
    terraform validate
```

Just validate. No plan/apply in CI yet.

---

## Implementation Order

1. Run `bootstrap.sh` — create remote state storage
2. Write `variables.tf` — subscription ID, location, prefix, environment
3. Write `main.tf` — resource group, ACR, Container Apps environment
4. Add Container App to `main.tf` — wire ACR credentials as secrets
5. Add Storage Account to `main.tf`
6. Add Static Web App to `main.tf`
7. Write `outputs.tf` — Container App URL, Static Web App URL, ACR login server
8. Run `terraform apply` in dev — first successful deploy

---

## Resolved Configuration

| Decision | Value |
|---|---|
| Storage | Local container storage — no import needed |
| Subscription | Visual Studio Enterprise Subscription |
| Region | `francecentral` |
| Naming prefix | `househelper` |

No open questions. Ready to implement.
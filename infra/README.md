# House Helper — Infrastructure (Terraform)

Provisions all Azure resources for House Helper:
- **Backend** — Azure Container App (FastAPI)
- **Frontend** — Azure Static Web App (React)
- **Container Registry** — ACR for Docker images
- **Storage Account** — Blob + Table storage for app data
- **Log Analytics** — Container App observability

---

## Prerequisites

Install and authenticate these tools before doing anything else:

```bash
# 1. Azure CLI
# https://learn.microsoft.com/en-us/cli/azure/install-azure-cli
az login
az account set --subscription "Visual Studio Enterprise Subscription"

# Confirm the right subscription is active
az account show --query "{name:name, id:id}" -o table

# 2. Terraform >= 1.7
# https://developer.hashicorp.com/terraform/install
terraform -version
```

---

## How it works — the two-phase deploy

Terraform needs somewhere to store its state file. That storage must exist **before** Terraform runs for the first time (it can't create its own state bucket). This gives us two phases:

```
Phase 1 — bootstrap.sh        Creates the state storage account (az CLI, once)
Phase 2 — terraform apply     Creates all app resources, writes state to that account
```

The state storage account (`rg-househelper-tfstate` / `sthousehelpertfstate`) is intentionally **outside** of Terraform — it's managed by `bootstrap.sh` and never touched by `terraform destroy`.

---

## Step-by-step: blank slate to running infra

### Step 1 — Bootstrap the Terraform state storage

```bash
cd infra/
./bootstrap.sh
```

This creates (if they don't already exist):

| What | Name |
|------|------|
| Resource group | `rg-househelper-tfstate` (westeurope) |
| Storage account | `sthousehelpertfstate` |
| Blob container | `tfstate` |

The script is **idempotent** — safe to re-run. It skips anything that already exists.

> **Have an existing storage account?** Pass it as the second argument:
> ```bash
> ./bootstrap.sh westeurope my-existing-storage-account
> ```
> The script locates its resource group automatically and creates only the `tfstate` container inside it.

---

### Step 2 — Initialise Terraform

```bash
terraform init
```

This downloads the `hashicorp/azurerm` provider and connects to the remote backend at `sthousehelpertfstate/tfstate`. You should see:

```
Initializing the backend...
Successfully configured the backend "azurerm"!
```

If you see an authentication error, re-run `az login` and make sure the right subscription is active.

---

### Step 3 — Configure your variables

```bash
cp terraform.tfvars.example terraform.tfvars
```

Find your subscription ID and fill it in:

```bash
az account show --query id -o tsv
```

Open `terraform.tfvars` and set:

```hcl
subscription_id = "YOUR-SUBSCRIPTION-ID-HERE"
```

Leave `backend_image` as-is for now — you'll update it after the ACR exists (Step 5).

`terraform.tfvars` is gitignored. **Never commit it.**

---

### Step 4 — Preview and apply

```bash
# See what will be created (no changes made)
terraform plan -var-file=terraform.tfvars

# Create the resources — Terraform writes state to sthousehelpertfstate/tfstate/dev.terraform.tfstate
terraform apply -var-file=terraform.tfvars
```

After a successful apply:

| Output | Example value |
|--------|---------------|
| `backend_url` | `ca-househelper-dev-backend.{region}.azurecontainerapps.io` |
| `frontend_url` | `stapp-househelper-dev.{hash}.azurestaticapps.net` |
| `acr_login_server` | `crhousehelperdev.azurecr.io` |
| `storage_account_name` | `sthousehelperdev` |

Every subsequent `plan` or `apply` reads from the remote state to compute what changed.

---

### Step 5 — Push a backend image and redeploy

The Container App needs a real image in the registry:

```bash
# Log in to the registry
az acr login --name crhousehelperdev

# Build and push from the repo root
docker build -t crhousehelperdev.azurecr.io/backend:latest ./backend
docker push crhousehelperdev.azurecr.io/backend:latest

# Re-apply (backend_image in terraform.tfvars already points here)
terraform apply -var-file=terraform.tfvars
```

---

## Tearing down

```bash
# Destroy all app resources (leaves the state storage account intact)
terraform destroy -var-file=terraform.tfvars

# Full clean — also remove the state storage
az group delete --name rg-househelper-tfstate --yes
```

---

## CI

`terraform validate -backend=false` runs in CI on every push and PR. It checks syntax and provider references without connecting to Azure or needing credentials.

---

## Files

| File | Purpose |
|------|---------|
| `bootstrap.sh` | One-time state storage setup — run before `terraform init` |
| `main.tf` | All Azure resources + remote backend config |
| `variables.tf` | Input variable definitions |
| `outputs.tf` | Values printed after apply |
| `terraform.tfvars.example` | Copy → `terraform.tfvars`, fill in subscription ID |
| `.gitignore` | Prevents committing state files and real `.tfvars` |

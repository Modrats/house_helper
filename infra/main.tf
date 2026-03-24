terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.90"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-househelper-tfstate"
    storage_account_name = "sthousehelpertfstate"
    container_name       = "tfstate"
    key                  = "dev.terraform.tfstate"
  }
}

provider "azurerm" {
  subscription_id = var.subscription_id

  features {}
}

# 1. Resource Group
resource "azurerm_resource_group" "main" {
  name     = "rg-${var.app_prefix}-${var.environment}"
  location = var.location
}

# 2. Container Registry
# ACR names must be globally unique and alphanumeric only — no hyphens. CAF prefix: cr.
resource "azurerm_container_registry" "main" {
  name                = "cr${var.app_prefix}${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Basic"
  admin_enabled       = true # required for Container Apps to pull images

  tags = {
    environment = var.environment
  }
}

# 3. Log Analytics Workspace (required by Container Apps Environment)
resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${var.app_prefix}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# 4. Container Apps Environment
resource "azurerm_container_app_environment" "main" {
  name                       = "cae-${var.app_prefix}-${var.environment}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  tags = {
    environment = var.environment
  }
}

# 5. Container App (backend FastAPI)
resource "azurerm_container_app" "backend" {
  name                         = "ca-${var.app_prefix}-${var.environment}-backend"
  location                     = azurerm_resource_group.main.location
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.main.admin_password
  }

  registry {
    server               = azurerm_container_registry.main.login_server
    username             = azurerm_container_registry.main.admin_username
    password_secret_name = "acr-password"
  }

  template {
    min_replicas = var.backend_min_replicas
    max_replicas = var.backend_max_replicas

    container {
      name   = "backend"
      image  = var.backend_image
      cpu    = var.backend_cpu
      memory = var.backend_memory
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}

# 6. Storage Account (Blob + Tables for app data)
# Storage account names must be alphanumeric only — no hyphens. CAF prefix: st.
resource "azurerm_storage_account" "main" {
  name                     = "st${var.app_prefix}${var.environment}"
  location                 = azurerm_resource_group.main.location
  resource_group_name      = azurerm_resource_group.main.name
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  tags = {
    environment = var.environment
  }
}

# 7. Static Web App (React frontend)
resource "azurerm_static_web_app" "frontend" {
  name                = "stapp-${var.app_prefix}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  sku_tier            = "Free"
  sku_size            = "Free"

  tags = {
    environment = var.environment
  }
}

output "backend_url" {
  description = "Backend API base URL"
  value       = azurerm_container_app.backend.latest_revision_fqdn
}

output "container_app_name" {
  description = "Container App resource name (used by deploy-backend)"
  value       = azurerm_container_app.backend.name
}

output "frontend_url" {
  description = "Frontend Static Web App URL"
  value       = azurerm_static_web_app.frontend.default_host_name
}

output "acr_login_server" {
  description = "ACR login server for docker push"
  value       = azurerm_container_registry.main.login_server
}

output "storage_account_name" {
  description = "Storage account name for app data"
  value       = azurerm_storage_account.main.name
}

output "swa_name" {
  description = "Static Web App resource name (used by deploy-frontend)"
  value       = azurerm_static_web_app.frontend.name
}

output "resource_group_name" {
  description = "Main resource group name"
  value       = azurerm_resource_group.main.name
}

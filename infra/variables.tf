variable "subscription_id" {
  description = "Azure subscription ID to deploy resources into. Must be set explicitly — no default."
  type        = string
}

variable "location" {
  description = "Primary Azure region for all resources."
  type        = string
  default     = "westeurope"
}

variable "app_prefix" {
  description = "Short prefix used in all resource names (e.g. 'househelper')."
  type        = string
  default     = "househelper"
}

variable "environment" {
  description = "Deployment environment label (e.g. 'dev', 'staging', 'prod')."
  type        = string
  default     = "dev"
}

variable "backend_image" {
  description = "Full ACR image reference for the backend container (e.g. househelperacr.azurecr.io/backend:latest). Must be set explicitly — no default."
  type        = string
}

variable "backend_cpu" {
  description = "vCPU allocation for the backend Container App."
  type        = number
  default     = 0.5
}

variable "backend_memory" {
  description = "Memory allocation for the backend Container App (e.g. '1Gi')."
  type        = string
  default     = "1Gi"
}

variable "backend_min_replicas" {
  description = "Minimum replica count for the backend Container App. Set to 0 to enable scale-to-zero in dev."
  type        = number
  default     = 0
}

variable "backend_max_replicas" {
  description = "Maximum replica count for the backend Container App."
  type        = number
  default     = 3
}

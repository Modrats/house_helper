### 2026-03-24: Static Web Apps must use westeurope, not francecentral
**By:** Zero
**What:** azurerm_static_web_app does not support francecentral. Used westeurope for SWA only; all other resources use francecentral.
**Why:** Azure limitation — SWA region availability is restricted.

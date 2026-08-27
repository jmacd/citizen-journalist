provider "azuread" {
  tenant_id = var.azure_tenant_id
}

provider "azurerm" {
  features {}

  subscription_id = var.azure_subscription_id
}

resource "azuread_application_registration" "foundry_runtime" {
  count        = var.foundry_identity_enabled ? 1 : 0
  display_name = "citizen-journalist-watershop"

  lifecycle {
    prevent_destroy = true
  }
}

resource "azuread_service_principal" "foundry_runtime" {
  count     = var.foundry_identity_enabled ? 1 : 0
  client_id = azuread_application_registration.foundry_runtime[0].client_id

  lifecycle {
    prevent_destroy = true
  }
}

resource "azuread_application_password" "foundry_runtime" {
  count          = var.foundry_identity_enabled ? 1 : 0
  application_id = azuread_application_registration.foundry_runtime[0].id
  display_name   = "watershop-runtime"
  end_date       = var.foundry_client_secret_end_date

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_role_assignment" "foundry_runtime" {
  count                = var.foundry_identity_enabled ? 1 : 0
  scope                = var.foundry_project_resource_id
  role_definition_name = "Foundry User"
  principal_id         = azuread_service_principal.foundry_runtime[0].object_id
  principal_type       = "ServicePrincipal"

  lifecycle {
    prevent_destroy = true
  }
}

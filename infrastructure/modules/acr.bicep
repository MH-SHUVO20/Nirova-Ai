// Azure Container Registry (ACR) Module
param acrName string
param location string = resourceGroup().location
param sku string = 'Standard'
param tags object = {}

resource acr 'Microsoft.ContainerRegistry/registries@2025-04-01' = {
  name: acrName
  location: location
  sku: {
    name: sku
  }
  identity: {
    type: 'SystemAssigned'
  }
  tags: tags
}

output acrLoginServer string = acr.properties.loginServer
output acrResourceId string = acr.id
output acrIdentityPrincipalId string = acr.identity.principalId

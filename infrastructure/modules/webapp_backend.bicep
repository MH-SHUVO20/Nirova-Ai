// Web App for Containers (Backend)
param name string
param location string = resourceGroup().location
param serverFarmId string
param imageName string
param acrLoginServer string
param appInsightsKey string
param keyVaultUri string
param tags object = {}

resource backend 'Microsoft.Web/sites@2024-11-01' = {
  name: name
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  kind: 'app,linux,container'
  properties: {
    serverFarmId: serverFarmId
    siteConfig: {
      linuxFxVersion: 'DOCKER|mcr.microsoft.com/azuredocs/aci-helloworld'
      appSettings: [
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsightsKey
        }
        {
          name: 'KEYVAULT_URI'
          value: keyVaultUri
        }
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
      ]
    }
    httpsOnly: true
  }
  tags: tags
}

output backendResourceId string = backend.id
output backendPrincipalId string = backend.identity.principalId

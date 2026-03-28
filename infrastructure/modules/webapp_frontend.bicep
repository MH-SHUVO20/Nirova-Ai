// Web App for Containers (Frontend)
param name string
param location string = resourceGroup().location
param serverFarmId string
param imageName string
param acrLoginServer string
param appInsightsKey string
param tags object = {}

resource frontend 'Microsoft.Web/sites@2024-11-01' = {
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
      ]
    }
    httpsOnly: true
  }
  tags: tags
}

output frontendResourceId string = frontend.id
output frontendPrincipalId string = frontend.identity.principalId

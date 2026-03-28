// Application Insights Module
param name string
param location string = resourceGroup().location
param workspaceResourceId string = ''
param tags object = {}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: name
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspaceResourceId
    publicNetworkAccessForIngestion: 'Disabled'
    publicNetworkAccessForQuery: 'Disabled'
  }
  tags: tags
}

output appInsightsKey string = appInsights.properties.InstrumentationKey
output appInsightsResourceId string = appInsights.id

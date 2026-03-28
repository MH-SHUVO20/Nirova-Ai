// Cosmos DB (MongoDB API) Module
param name string
param location string = resourceGroup().location
param kind string = 'MongoDB'
param enablePrivateEndpoint bool = true
param tags object = {}

resource cosmosdb 'Microsoft.DocumentDB/databaseAccounts@2025-04-15' = {
  name: name
  location: location
  kind: kind
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: [
      {
        name: 'EnableMongo'
      }
    ]
    enableFreeTier: false
    isVirtualNetworkFilterEnabled: enablePrivateEndpoint
    publicNetworkAccess: enablePrivateEndpoint ? 'Disabled' : 'Enabled'
  }
  tags: tags
}

output cosmosdbResourceId string = cosmosdb.id
output cosmosdbEndpoint string = cosmosdb.properties.documentEndpoint
output cosmosdbPrincipalId string = cosmosdb.identity.principalId

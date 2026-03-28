// Azure Storage Account Module
param name string
param location string = resourceGroup().location
param kind string = 'StorageV2'
param skuName string = 'Standard_LRS'
param enablePrivateEndpoint bool = true
param tags object = {}

resource storage 'Microsoft.Storage/storageAccounts@2025-01-01' = {
  name: name
  location: location
  kind: kind
  sku: {
    name: skuName
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: enablePrivateEndpoint ? 'Disabled' : 'Enabled'
  }
  tags: tags
}

output storageResourceId string = storage.id
output storageBlobEndpoint string = storage.properties.primaryEndpoints.blob
output storagePrincipalId string = storage.identity.principalId

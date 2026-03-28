// Azure Key Vault Module
param name string
param location string = resourceGroup().location
param tenantId string
param objectIds array
param tags object = {}

resource keyVault 'Microsoft.KeyVault/vaults@2024-11-01' = {
  name: name
  location: location
  properties: {
    tenantId: tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    accessPolicies: [
      for objectId in objectIds: {
        tenantId: tenantId
        objectId: objectId
        permissions: {
          secrets: [ 'get', 'list', 'set', 'delete', 'backup', 'restore', 'recover', 'purge' ]
        }
      }
    ]
    enabledForDeployment: true
    enabledForTemplateDeployment: true
    enabledForDiskEncryption: true
    enableRbacAuthorization: true
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Deny'
    }
  }
  tags: tags
}

output keyVaultUri string = keyVault.properties.vaultUri
output keyVaultResourceId string = keyVault.id

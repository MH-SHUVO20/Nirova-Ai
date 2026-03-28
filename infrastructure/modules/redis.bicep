// Azure Cache for Redis Module
param name string
param location string = resourceGroup().location
param skuName string = 'Standard'
param skuFamily string = 'C'
param skuCapacity int = 1
param enablePrivateEndpoint bool = true
param tags object = {}

resource redis 'Microsoft.Cache/redis@2024-11-01' = {
  name: name
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    sku: {
      name: skuName
      family: skuFamily
      capacity: skuCapacity
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    publicNetworkAccess: enablePrivateEndpoint ? 'Disabled' : 'Enabled'
  }
  tags: tags
}

output redisResourceId string = redis.id
output redisHostName string = redis.properties.hostName
output redisPrincipalId string = redis.identity.principalId

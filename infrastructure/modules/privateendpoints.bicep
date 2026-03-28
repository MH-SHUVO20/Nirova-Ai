// Private Endpoints Module
param name string
param location string = resourceGroup().location
param subnetId string
param resourceId string
param groupId string
param tags object = {}

resource pe 'Microsoft.Network/privateEndpoints@2023-09-01' = {
  name: name
  location: location
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: name + '-pls'
        privateLinkServiceId: resourceId
        groupIds: [ groupId ]
      }
    ]
  }
  tags: tags
}

output privateEndpointId string = pe.id

// Main Bicep file for Nirova-Ai Azure Infrastructure
param location string = resourceGroup().location
param env string = 'dev'
param tags object = {
  environment: env
  project: 'Nirova-Ai'
}

// Parameterized names
param acrName string
param backendName string
param frontendName string
param cosmosdbName string
param redisName string
param storageName string
param keyVaultName string
param appInsightsName string
param tenantId string
param objectIds array

// Container Registry
module acr 'modules/acr.bicep' = {
  name: 'acrDeploy'
  params: {
    acrName: acrName
    location: location
    tags: tags
  }
}

// Application Insights
module appinsights 'modules/appinsights.bicep' = {
  name: 'appInsightsDeploy'
  params: {
    name: appInsightsName
    location: location
    tags: tags
  }
}

// Key Vault
module keyvault 'modules/keyvault.bicep' = {
  name: 'keyVaultDeploy'
  params: {
    name: keyVaultName
    location: location
    tenantId: tenantId
    objectIds: objectIds
    tags: tags
  }
}

// Cosmos DB (MongoDB API)
module cosmosdb 'modules/cosmosdb.bicep' = {
  name: 'cosmosDbDeploy'
  params: {
    name: cosmosdbName
    location: location
    tags: tags
  }
}

// Redis
module redis 'modules/redis.bicep' = {
  name: 'redisDeploy'
  params: {
    name: redisName
    location: location
    tags: tags
  }
}

// Storage
module storage 'modules/storage.bicep' = {
  name: 'storageDeploy'
  params: {
    name: storageName
    location: location
    tags: tags
  }
}

// Web App Backend
module backend 'modules/webapp_backend.bicep' = {
  name: 'backendDeploy'
  params: {
    name: backendName
    location: location
    serverFarmId: '' // To be parameterized if using App Service Plan
    imageName: 'backend:latest'
    acrLoginServer: acr.outputs.acrLoginServer
    // acrIdentityPrincipalId removed: no longer required by module
    appInsightsKey: appinsights.outputs.appInsightsKey
    keyVaultUri: keyvault.outputs.keyVaultUri
    tags: tags
  }
}

// Web App Frontend
module frontend 'modules/webapp_frontend.bicep' = {
  name: 'frontendDeploy'
  params: {
    name: frontendName
    location: location
    serverFarmId: '' // To be parameterized if using App Service Plan
    imageName: 'frontend:latest'
    acrLoginServer: acr.outputs.acrLoginServer
    // acrIdentityPrincipalId removed: no longer required by module
    appInsightsKey: appinsights.outputs.appInsightsKey
    tags: tags
  }
}

import { defineConfig } from '@hey-api/openapi-ts'

export default defineConfig({
  input: process.env.OPENAPI_SPEC_URL || 'http://127.0.0.1:8080/openapi.json',
  output: {
    path: 'src/shared/api/generated',
    clean: true
  },
  plugins: [
    '@hey-api/typescript',
    {
      name: '@hey-api/sdk',
      operations: {
        strategy: 'single'
      }
    },
    '@hey-api/client-fetch'
  ]
})

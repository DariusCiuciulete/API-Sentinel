# API Sentinel Examples

This directory contains sample files for testing API Sentinel's discovery and monitoring features.

## Contents

- `petstore_openapi.yaml` - Sample OpenAPI 3.0 specification (Petstore API)
- `sample_api_docs.html` - Sample HTML API documentation
- `mock_api.py` - Simple mock API server for testing monitoring
- `mock_api_spec.yaml` - OpenAPI spec for the mock API

## Usage

### 1. Test Discovery with OpenAPI Spec

Upload `petstore_openapi.yaml` via the Discovery page in API Sentinel.

### 2. Test Discovery with Documentation

Upload `sample_api_docs.html` via the Discovery page.

### 3. Test Monitoring

1. Run the mock API:
   ```bash
   python mock_api.py
   ```

2. Upload `mock_api_spec.yaml` to discover endpoints

3. Go to Monitoring page and run monitoring checks

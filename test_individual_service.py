#!/usr/bin/env python3
"""
Test individual services without Docker to check implementation
"""

import sys
import os
import asyncio
from pathlib import Path

# Add services to path
sys.path.append(str(Path(__file__).parent))

async def test_embedding_service():
    """Test embedding service directly"""
    print("🧪 Testing Embedding Service Implementation...")
    
    try:
        # Import the service
        from services.embedding_service.app.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/health")
        print(f"  Health Check: {response.status_code}")
        
        if response.status_code == 200:
            print(f"  Response: {response.json()}")
            
            # Test embedding generation
            test_data = {
                "texts": ["Bitcoin is a cryptocurrency", "Ethereum smart contracts"],
                "normalize": True
            }
            
            embed_response = client.post("/embed", json=test_data)
            print(f"  Embedding Test: {embed_response.status_code}")
            
            if embed_response.status_code == 200:
                result = embed_response.json()
                print(f"  ✅ Embeddings generated: {len(result.get('embeddings', []))}")
                print(f"  ✅ Dimensions: {result.get('dimensions', 0)}")
                return True
        
        return False
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

async def test_storage_service():
    """Test storage service directly"""
    print("\n🧪 Testing Storage Service Implementation...")
    
    try:
        from services.storage_service.app.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/health")
        print(f"  Health Check: {response.status_code}")
        
        if response.status_code == 200:
            print(f"  Response: {response.json()}")
            return True
        
        return False
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

async def test_vector_retrieval_service():
    """Test vector retrieval service directly"""
    print("\n🧪 Testing Vector Retrieval Service Implementation...")
    
    try:
        from services.vector_retrieval_service.app.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/health")
        print(f"  Health Check: {response.status_code}")
        
        if response.status_code == 200:
            print(f"  Response: {response.json()}")
            return True
        
        return False
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

async def test_ingestion_service():
    """Test ingestion service directly"""
    print("\n🧪 Testing Ingestion Service Implementation...")
    
    try:
        from services.ingestion_service.app.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/health")
        print(f"  Health Check: {response.status_code}")
        
        if response.status_code == 200:
            print(f"  Response: {response.json()}")
            return True
        
        return False
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

async def main():
    """Run all service tests"""
    print("🚀 Testing Crypto Knowledge System Services")
    print("=" * 50)
    
    results = {}
    
    # Test each service
    results["embedding"] = await test_embedding_service()
    results["storage"] = await test_storage_service()
    results["vector_retrieval"] = await test_vector_retrieval_service()
    results["ingestion"] = await test_ingestion_service()
    
    # Summary
    print("\n📊 TEST RESULTS SUMMARY")
    print("=" * 30)
    
    passed = sum(results.values())
    total = len(results)
    
    for service, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {service.replace('_', ' ').title()}: {status}")
    
    print(f"\nOverall: {passed}/{total} services working")
    
    if passed == total:
        print("🎉 All services are working correctly!")
    elif passed >= total * 0.7:
        print("⚠️  Most services working, some issues detected")
    else:
        print("🚨 Multiple service failures detected")

if __name__ == "__main__":
    asyncio.run(main())
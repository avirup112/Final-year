#!/usr/bin/env python3
"""
Test script to validate the crypto knowledge system services
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, List, Any

class ServiceTester:
    def __init__(self):
        self.services = {
            "ingestion-service": "http://localhost:8001",
            "fact-extraction-service": "http://localhost:8002", 
            "embedding-service": "http://localhost:8003",
            "storage-service": "http://localhost:8004",
            "vector-retrieval-service": "http://localhost:8005",
            "llm-generator-service": "http://localhost:8006",
            "self-healing-service": "http://localhost:8007",
            "cache-service": "http://localhost:8008",
            "api-gateway": "http://localhost:8080",
            "ui-service": "http://localhost:8501"
        }
        
        self.results = {}
    
    async def test_service_health(self, service_name: str, base_url: str) -> Dict[str, Any]:
        """Test individual service health"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{base_url}/health")
                
                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "response_time": response.elapsed.total_seconds(),
                        "data": response.json()
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "status_code": response.status_code,
                        "error": response.text
                    }
                    
        except Exception as e:
            return {
                "status": "unreachable",
                "error": str(e)
            }
    
    async def test_embedding_service(self) -> Dict[str, Any]:
        """Test embedding service functionality"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                test_data = {
                    "texts": ["Bitcoin price is rising", "Ethereum smart contracts"],
                    "normalize": True
                }
                
                response = await client.post(
                    f"{self.services['embedding-service']}/embed",
                    json=test_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "status": "success",
                        "embeddings_generated": len(result.get("embeddings", [])),
                        "dimensions": result.get("dimensions", 0),
                        "model": result.get("model_name", "unknown")
                    }
                else:
                    return {"status": "failed", "error": response.text}
                    
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def test_ingestion_service(self) -> Dict[str, Any]:
        """Test ingestion service functionality"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test manual fetch
                test_data = {
                    "symbols": ["bitcoin", "ethereum"],
                    "sources": ["coingecko"],
                    "force": True
                }
                
                response = await client.post(
                    f"{self.services['ingestion-service']}/fetch-now",
                    json=test_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "status": "success",
                        "fetch_triggered": True,
                        "symbols_processed": result.get("symbols_processed", 0)
                    }
                else:
                    return {"status": "failed", "error": response.text}
                    
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def test_storage_service(self) -> Dict[str, Any]:
        """Test storage service functionality"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test storing a fact
                test_fact = {
                    "content": "Bitcoin reached a new all-time high",
                    "source": "test",
                    "category": "price",
                    "confidence_score": 0.95,
                    "metadata": {"test": True}
                }
                
                response = await client.post(
                    f"{self.services['storage-service']}/facts",
                    json=test_fact
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "status": "success",
                        "fact_stored": True,
                        "fact_id": result.get("id")
                    }
                else:
                    return {"status": "failed", "error": response.text}
                    
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def test_vector_retrieval_service(self) -> Dict[str, Any]:
        """Test vector retrieval service functionality"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test RAG query
                test_query = {
                    "question": "What is Bitcoin?",
                    "n_results": 3,
                    "collection_name": "crypto_facts"
                }
                
                response = await client.post(
                    f"{self.services['vector-retrieval-service']}/rag-query",
                    json=test_query
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "status": "success",
                        "context_found": len(result.get("context", [])),
                        "confidence_score": result.get("confidence_score", 0)
                    }
                else:
                    return {"status": "failed", "error": response.text}
                    
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🚀 Starting Crypto Knowledge System Tests")
        print("=" * 50)
        
        # Test 1: Health checks for all services
        print("\n📋 Testing Service Health...")
        health_tasks = [
            self.test_service_health(name, url) 
            for name, url in self.services.items()
        ]
        
        health_results = await asyncio.gather(*health_tasks, return_exceptions=True)
        
        for i, (service_name, result) in enumerate(zip(self.services.keys(), health_results)):
            if isinstance(result, Exception):
                result = {"status": "error", "error": str(result)}
            
            self.results[f"{service_name}_health"] = result
            status_emoji = "✅" if result.get("status") == "healthy" else "❌"
            print(f"  {status_emoji} {service_name}: {result.get('status', 'unknown')}")
        
        # Test 2: Functional tests for implemented services
        print("\n🔧 Testing Service Functionality...")
        
        # Test embedding service
        print("  Testing Embedding Service...")
        embedding_result = await self.test_embedding_service()
        self.results["embedding_functionality"] = embedding_result
        status_emoji = "✅" if embedding_result.get("status") == "success" else "❌"
        print(f"    {status_emoji} Embeddings: {embedding_result.get('status')}")
        
        # Test ingestion service
        print("  Testing Ingestion Service...")
        ingestion_result = await self.test_ingestion_service()
        self.results["ingestion_functionality"] = ingestion_result
        status_emoji = "✅" if ingestion_result.get("status") == "success" else "❌"
        print(f"    {status_emoji} Data Ingestion: {ingestion_result.get('status')}")
        
        # Test storage service
        print("  Testing Storage Service...")
        storage_result = await self.test_storage_service()
        self.results["storage_functionality"] = storage_result
        status_emoji = "✅" if storage_result.get("status") == "success" else "❌"
        print(f"    {status_emoji} Data Storage: {storage_result.get('status')}")
        
        # Test vector retrieval service
        print("  Testing Vector Retrieval Service...")
        vector_result = await self.test_vector_retrieval_service()
        self.results["vector_functionality"] = vector_result
        status_emoji = "✅" if vector_result.get("status") == "success" else "❌"
        print(f"    {status_emoji} Vector Retrieval: {vector_result.get('status')}")
        
        # Generate summary
        self.generate_summary()
    
    def generate_summary(self):
        """Generate test summary report"""
        print("\n📊 TEST SUMMARY REPORT")
        print("=" * 50)
        
        # Count healthy services
        healthy_services = sum(
            1 for key, result in self.results.items() 
            if key.endswith("_health") and result.get("status") == "healthy"
        )
        total_services = len([k for k in self.results.keys() if k.endswith("_health")])
        
        # Count successful functionality tests
        successful_tests = sum(
            1 for key, result in self.results.items()
            if key.endswith("_functionality") and result.get("status") == "success"
        )
        total_tests = len([k for k in self.results.keys() if k.endswith("_functionality")])
        
        print(f"🏥 Service Health: {healthy_services}/{total_services} services healthy")
        print(f"⚡ Functionality: {successful_tests}/{total_tests} tests passed")
        
        # Overall system status
        if healthy_services >= total_services * 0.7 and successful_tests >= total_tests * 0.7:
            print("🎉 SYSTEM STATUS: OPERATIONAL")
        elif healthy_services >= total_services * 0.5:
            print("⚠️  SYSTEM STATUS: DEGRADED")
        else:
            print("🚨 SYSTEM STATUS: CRITICAL")
        
        # Detailed results
        print(f"\n📝 Detailed Results:")
        for key, result in self.results.items():
            print(f"  {key}: {json.dumps(result, indent=2)}")
        
        # Save results to file
        with open(f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "healthy_services": healthy_services,
                    "total_services": total_services,
                    "successful_tests": successful_tests,
                    "total_tests": total_tests
                },
                "detailed_results": self.results
            }, f, indent=2)
        
        print(f"\n💾 Results saved to test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

async def main():
    """Main test function"""
    tester = ServiceTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
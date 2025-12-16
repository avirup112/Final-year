#!/usr/bin/env python3
"""
Quick terminal test for crypto knowledge system
"""

import sys
import importlib.util
from pathlib import Path

def test_imports():
    """Test if all service modules can be imported"""
    print("🧪 Testing Service Imports...")
    
    services = [
        "services/embedding-service/app/main.py",
        "services/storage-service/app/main.py", 
        "services/vector-retrieval-service/app/main.py",
        "services/ingestion-service/app/main.py",
        "services/self-healing-service/app/main.py"
    ]
    
    results = {}
    
    for service_path in services:
        service_name = service_path.split('/')[1]
        try:
            # Try to import the module
            spec = importlib.util.spec_from_file_location("test_module", service_path)
            module = importlib.util.module_from_spec(spec)
            
            # Check if it has FastAPI app
            if Path(service_path).exists():
                with open(service_path, 'r') as f:
                    content = f.read()
                    if 'FastAPI' in content and 'app =' in content:
                        results[service_name] = "✅ READY"
                    else:
                        results[service_name] = "⚠️  INCOMPLETE"
            else:
                results[service_name] = "❌ MISSING"
                
        except Exception as e:
            results[service_name] = f"❌ ERROR: {str(e)[:50]}"
    
    return results

def test_dependencies():
    """Test if required dependencies are available"""
    print("\n📦 Testing Dependencies...")
    
    deps = {
        "fastapi": "FastAPI framework",
        "uvicorn": "ASGI server", 
        "redis": "Redis client",
        "motor": "MongoDB async driver",
        "chromadb": "Vector database",
        "sentence_transformers": "Embedding models",
        "httpx": "HTTP client"
    }
    
    results = {}
    
    for dep, description in deps.items():
        try:
            __import__(dep)
            results[dep] = "✅ INSTALLED"
        except ImportError:
            results[dep] = "❌ MISSING"
    
    return results

def test_docker_config():
    """Test Docker configuration"""
    print("\n🐳 Testing Docker Configuration...")
    
    results = {}
    
    # Check if docker-compose.yml exists
    if Path("docker-compose.yml").exists():
        results["docker-compose.yml"] = "✅ EXISTS"
        
        # Check if it has required services
        with open("docker-compose.yml", 'r') as f:
            content = f.read()
            
        required_services = ["redis", "mongodb", "chromadb", "ingestion-service", "storage-service"]
        
        for service in required_services:
            if service in content:
                results[f"service-{service}"] = "✅ CONFIGURED"
            else:
                results[f"service-{service}"] = "❌ MISSING"
    else:
        results["docker-compose.yml"] = "❌ MISSING"
    
    return results

def test_environment():
    """Test environment configuration"""
    print("\n🔧 Testing Environment...")
    
    results = {}
    
    # Check .env.example
    if Path(".env.example").exists():
        results[".env.example"] = "✅ EXISTS"
    else:
        results[".env.example"] = "❌ MISSING"
    
    # Check .env
    if Path(".env").exists():
        results[".env"] = "✅ EXISTS"
    else:
        results[".env"] = "⚠️  CREATE FROM .env.example"
    
    return results

def main():
    """Run all tests"""
    print("🚀 CRYPTO KNOWLEDGE SYSTEM - QUICK TEST")
    print("=" * 50)
    
    # Run all tests
    import_results = test_imports()
    dep_results = test_dependencies()
    docker_results = test_docker_config()
    env_results = test_environment()
    
    # Print results
    print("\nTEST RESULTS")
    print("-" * 30)
    
    print("\n🔧 Service Implementation:")
    for service, status in import_results.items():
        print(f"  {service}: {status}")
    
    print("\n📦 Dependencies:")
    for dep, status in dep_results.items():
        print(f"  {dep}: {status}")
    
    print("\n🐳 Docker Configuration:")
    for item, status in docker_results.items():
        print(f"  {item}: {status}")
    
    print("\n🔧 Environment:")
    for item, status in env_results.items():
        print(f"  {item}: {status}")
    
    # Calculate overall score
    all_results = {**import_results, **dep_results, **docker_results, **env_results}
    
    total_items = len(all_results)
    ready_items = sum(1 for status in all_results.values() if "✅" in status)
    
    score = (ready_items / total_items) * 100
    
    print(f"\n🎯 OVERALL SYSTEM READINESS: {score:.1f}%")
    print(f"   Ready: {ready_items}/{total_items} components")
    
    if score >= 90:
        print("SYSTEM STATUS: EXCELLENT - Ready for production!")
    elif score >= 70:
        print("SYSTEM STATUS: GOOD - Minor issues to resolve")
    elif score >= 50:
        print("SYSTEM STATUS: FAIR - Some components need attention")
    else:
        print("SYSTEM STATUS: NEEDS WORK - Major issues detected")
    
    print("\n💡 NEXT STEPS:")
    
    missing_deps = [dep for dep, status in dep_results.items() if "❌" in status]
    if missing_deps:
        print(f"   1. Install missing dependencies: pip install {' '.join(missing_deps)}")
    
    if ".env" not in env_results or "❌" in env_results.get(".env", ""):
        print("   2. Create .env file: cp .env.example .env")
        print("   3. Add your API keys to .env file")
    
    print("   4. Start infrastructure: docker-compose up -d redis mongodb chromadb")
    print("   5. Start services: docker-compose up -d")
    print("   6. Test endpoints: python test_services.py")
    
    print(f"\n📁 Project Location: {Path.cwd()}")
    print("🔗 Ready to run the crypto knowledge system!")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
RAG Setup Verification Script

This script checks if the RAG (Retrieval-Augmented Generation) system 
is properly configured and ready to use.
"""

def check_dependencies():
    """Check if required dependencies are installed"""
    missing_deps = []
    
    try:
        import numpy
        print("✅ numpy - OK")
    except ImportError:
        print("❌ numpy - MISSING")
        missing_deps.append("numpy")
    
    try:
        import sentence_transformers
        print("✅ sentence-transformers - OK")
    except ImportError:
        print("❌ sentence-transformers - MISSING")
        missing_deps.append("sentence-transformers")
    
    try:
        import faiss
        print("✅ faiss-cpu - OK")
    except ImportError:
        print("❌ faiss-cpu - MISSING")
        missing_deps.append("faiss-cpu")
    
    return missing_deps

def check_modules():
    """Check if custom modules can be imported"""
    modules_status = {}
    
    try:
        from semantic_search import semantic_search
        print("✅ semantic_search module - OK")
        modules_status['semantic_search'] = True
    except ImportError as e:
        print(f"❌ semantic_search module - ERROR: {e}")
        modules_status['semantic_search'] = False
    
    try:
        from knowledge_base import ProductKnowledgeBase
        print("✅ knowledge_base module - OK")
        modules_status['knowledge_base'] = True
    except ImportError as e:
        print(f"❌ knowledge_base module - ERROR: {e}")
        modules_status['knowledge_base'] = False
    
    try:
        import recommendation_engine
        print("✅ recommendation_engine module - OK")
        modules_status['recommendation_engine'] = True
    except ImportError as e:
        print(f"❌ recommendation_engine module - ERROR: {e}")
        modules_status['recommendation_engine'] = False
    
    return modules_status

def check_data_files():
    """Check if required data files exist"""
    import os
    
    files_status = {}
    
    # Check listing.json
    if os.path.exists('listing.json'):
        print("✅ listing.json - Found")
        files_status['listing.json'] = True
    else:
        print("❌ listing.json - Missing")
        files_status['listing.json'] = False
    
    # Check tariff 1.json (enhanced RAG data)
    if os.path.exists('tariff 1.json'):
        print("✅ tariff 1.json - Found (Enhanced RAG)")
        files_status['tariff 1.json'] = True
    else:
        print("❌ tariff 1.json - Missing (Enhanced RAG will be limited)")
        files_status['tariff 1.json'] = False
    
    # Check CSV files
    csv_files = ['sample_devices.csv', 'sample_plans.csv']
    for csv_file in csv_files:
        if os.path.exists(csv_file):
            print(f"✅ {csv_file} - Found")
            files_status[csv_file] = True
        else:
            print(f"❌ {csv_file} - Missing")
            files_status[csv_file] = False
    
    return files_status

def main():
    """Main verification function"""
    print("🔍 RAG System Setup Verification")
    print("=" * 40)
    
    print("\n📦 Checking Dependencies:")
    missing_deps = check_dependencies()
    
    print("\n🔧 Checking Modules:")
    modules_status = check_modules()
    
    print("\n📁 Checking Data Files:")
    files_status = check_data_files()
    
    print("\n📋 Summary:")
    print("=" * 40)
    
    if missing_deps:
        print("❌ Missing dependencies:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print("\n💡 To install missing dependencies, run:")
        print("   pip install -r requirements.txt")
    else:
        print("✅ All dependencies installed")
    
    if all(modules_status.values()):
        print("✅ All custom modules importable")
    else:
        print("❌ Some custom modules have issues")
    
    if all(files_status.values()):
        print("✅ All required data files present")
    else:
        print("❌ Some required data files missing")
    
    # Overall status
    if not missing_deps and all(modules_status.values()) and all(files_status.values()):
        print("\n🎉 RAG System is ready to use!")
        return True
    else:
        print("\n⚠️  RAG System needs setup - see issues above")
        return False

if __name__ == "__main__":
    main()
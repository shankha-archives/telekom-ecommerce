#!/usr/bin/env python3
"""
Enhanced RAG System Test Script

This script tests the enhanced RAG functionality with tariff data integration.
"""

def test_knowledge_base():
    """Test enhanced knowledge base loading"""
    print("🧪 Testing Enhanced Knowledge Base")
    print("-" * 40)
    
    try:
        from knowledge_base import initialize_knowledge_base, knowledge_base
        
        # Initialize with both data sources
        success = initialize_knowledge_base("listing.json", "tariff 1.json")
        
        if success:
            print("✅ Enhanced knowledge base loaded successfully")
            print(f"  📊 Device specs: {len(knowledge_base.device_specs)}")
            print(f"  📊 Plan details: {len(knowledge_base.plan_details)}")
            print(f"  📊 Tariff data: {len(knowledge_base.tariff_data)}")
            print(f"  📊 Unified plans: {len(knowledge_base.unified_plans)}")
            
            # Test enhanced plan context
            if knowledge_base.tariff_data:
                first_tariff_id = next(iter(knowledge_base.tariff_data.keys()))
                context = knowledge_base.get_enhanced_plan_context(first_tariff_id)
                print(f"  📋 Sample plan context length: {len(context)} chars")
                return True
        else:
            print("❌ Enhanced knowledge base loading failed")
            return False
            
    except Exception as e:
        print(f"❌ Knowledge base test error: {e}")
        return False

def test_semantic_search():
    """Test enhanced semantic search with tariff data"""
    print("\n🔍 Testing Enhanced Semantic Search")
    print("-" * 40)
    
    try:
        # Load sample data
        import csv
        import json
        
        # Load CSV plans
        plans = []
        try:
            with open('sample_plans.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    plans.append({
                        'id': row['id'],
                        'name': row['name'],
                        'data': row['data'],
                        'price': row['price'],
                        'features': row['features'].split(';') if row['features'] else []
                    })
        except:
            print("⚠️  Sample plans CSV not available")
            return False
        
        # Load tariff data
        tariff_data = {}
        try:
            with open('tariff 1.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                sales_offerings = data.get('salesOfferings', [])
                for offering in sales_offerings[:5]:  # Test with first 5
                    product_data = offering.get('productOffering', {})
                    product_id = product_data.get('id', '')
                    if product_id:
                        tariff_data[product_id] = product_data
        except:
            print("⚠️  Tariff data not available")
        
        # Initialize semantic search
        from semantic_search import initialize_semantic_search
        
        success = initialize_semantic_search([], plans, tariff_data)
        
        if success:
            print("✅ Enhanced semantic search initialized")
            print(f"  📊 Plans indexed: {len(plans)}")
            print(f"  📊 Tariff data: {len(tariff_data)} entries")
            
            # Test semantic search queries
            test_queries = [
                "unlimited data for streaming",
                "family plan with international roaming",
                "budget plan under 30 euros"
            ]
            
            from semantic_search import semantic_search_products
            
            for query in test_queries:
                results = semantic_search_products(query, "plans")
                plan_results = results.get("plans", [])
                print(f"  🔍 '{query}' -> {len(plan_results)} matches")
            
            return True
        else:
            print("❌ Enhanced semantic search initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Semantic search test error: {e}")
        return False

def test_integration():
    """Test full integration"""
    print("\n🔗 Testing Full RAG Integration")
    print("-" * 40)
    
    try:
        # Test the integration that would happen in server.py
        from knowledge_base import initialize_knowledge_base
        import recommendation_engine
        
        # Initialize knowledge base
        kb_success = initialize_knowledge_base("listing.json", "tariff 1.json")
        
        # Load sample data (simplified)
        devices = [{"id": "test_device", "name": "Test Device"}]
        plans = [{"id": "test_plan", "name": "Test Plan", "data": "5GB", "price": "25"}]
        
        # Initialize RAG system
        rag_success = recommendation_engine.initialize_rag_system(devices, plans)
        
        if kb_success and rag_success:
            print("✅ Full RAG integration successful")
            print("  📊 Knowledge base: ✅")
            print("  📊 Semantic search: ✅")
            print("  📊 Recommendation engine: ✅")
            return True
        else:
            print(f"❌ Integration failed (KB: {kb_success}, RAG: {rag_success})")
            return False
            
    except Exception as e:
        print(f"❌ Integration test error: {e}")
        return False

def main():
    """Run all enhanced RAG tests"""
    print("🚀 Enhanced RAG System Test Suite")
    print("=" * 50)
    
    tests = [
        ("Knowledge Base", test_knowledge_base),
        ("Semantic Search", test_semantic_search),
        ("Full Integration", test_integration)
    ]
    
    results = {}
    for test_name, test_func in tests:
        results[test_name] = test_func()
    
    print("\n📋 Test Results Summary")
    print("=" * 50)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All enhanced RAG tests passed!")
        print("💡 Your system is ready for enhanced recommendations with tariff data.")
    else:
        print("\n⚠️  Some enhanced RAG tests failed.")
        print("💡 Install dependencies with: pip install -r requirements.txt")
    
    return all_passed

if __name__ == "__main__":
    main()
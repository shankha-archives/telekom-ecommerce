"""
Knowledge Base Module for Rich Product Information

This module parses the detailed listing.json file to extract rich product information
for enhanced RAG capabilities.
"""

import json
import logging
from typing import Dict, List, Optional

class ProductKnowledgeBase:
    """
    Enhanced knowledge base for detailed product information from multiple sources:
    - listing.json: Device specifications and basic product info
    - tariff 1.json: Rich tariff/plan details with comprehensive characteristics
    """
    
    def __init__(self, listing_file: str = "listing.json", tariff_file: str = "tariff 1.json"):
        self.listing_file = listing_file
        self.tariff_file = tariff_file
        self.products = {}
        self.device_specs = {}
        self.plan_details = {}
        self.tariff_data = {}
        self.unified_plans = {}
        self.initialized = False
    
    def load_listing_data(self) -> bool:
        """
        Load and parse the listing.json file
        
        Returns:
            bool: Success status
        """
        try:
            with open(self.listing_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract product offerings
            offerings = data.get('productOfferings', [])
            
            for offering in offerings:
                product_data = offering.get('productOffering', {})
                product_id = product_data.get('id', '')
                product_name = product_data.get('name', '')
                product_group = product_data.get('group', '')
                
                if not product_id:
                    continue
                
                # Parse characteristics for detailed specs
                characteristics = product_data.get('characteristics', [])
                specs = self._parse_characteristics(characteristics)
                
                # Store product information
                product_info = {
                    'id': product_id,
                    'name': product_name,
                    'group': product_group,
                    'description': product_data.get('description', ''),
                    'shortDescription': product_data.get('shortDescription', ''),
                    'specs': specs,
                    'raw_data': product_data,
                    'source': 'listing'
                }
                
                self.products[product_id] = product_info
                
                # Categorize by product type
                if product_group == 'device':
                    self.device_specs[product_id] = product_info
                elif product_group in ['plan', 'tariff'] or 'plan' in product_name.lower():
                    self.plan_details[product_id] = product_info
            
            logging.info(f"Listing data loaded: {len(self.products)} products, {len(self.device_specs)} devices, {len(self.plan_details)} plans")
            return True
            
        except Exception as e:
            logging.error(f"Failed to load listing data: {str(e)}")
            return False
    
    def load_tariff_data(self) -> bool:
        """
        Load and parse the tariff 1.json file for rich plan/tariff information
        
        Returns:
            bool: Success status
        """
        try:
            with open(self.tariff_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract sales offerings (tariff plans)
            sales_offerings = data.get('salesOfferings', [])
            
            for offering in sales_offerings:
                product_data = offering.get('productOffering', {})
                product_id = product_data.get('id', '')
                product_name = product_data.get('name', '')
                product_group = product_data.get('group', '')
                business_group = product_data.get('businessGroup', '')
                
                if not product_id:
                    continue
                
                # Parse characteristics for detailed tariff specs
                characteristics = product_data.get('characteristics', [])
                tariff_specs = self._parse_tariff_characteristics(characteristics)
                
                # Store tariff information
                tariff_info = {
                    'id': product_id,
                    'name': product_name,
                    'group': product_group,
                    'businessGroup': business_group,
                    'description': product_data.get('description', ''),
                    'shortDescription': product_data.get('shortDescription', ''),
                    'tariff_specs': tariff_specs,
                    'raw_data': product_data,
                    'source': 'tariff'
                }
                
                self.tariff_data[product_id] = tariff_info
                
                # Add to unified plans if it's a tariff
                if product_group == 'tariff' or business_group == 'TARIFF':
                    self.unified_plans[product_id] = tariff_info
            
            logging.info(f"Tariff data loaded: {len(self.tariff_data)} tariffs, {len(self.unified_plans)} unified plans")
            return True
            
        except Exception as e:
            logging.error(f"Failed to load tariff data: {str(e)}")
            return False
    
    def _parse_tariff_characteristics(self, characteristics: List[Dict]) -> Dict:
        """
        Parse tariff characteristics into structured specs with enhanced context
        
        Args:
            characteristics: List of characteristic dictionaries from tariff data
            
        Returns:
            Dict: Parsed tariff specifications
        """
        specs = {}
        
        for char in characteristics:
            char_name = char.get('name', '')
            char_label = char.get('label', char_name)
            char_values = char.get('characteristicValues', [])
            
            if not char_name or not char_values:
                continue
            
            # Extract values with enhanced semantic context
            values = []
            semantic_context = []
            
            for val in char_values:
                value = val.get('value', '')
                label = val.get('label', value)
                if value and label:
                    values.append({'value': value, 'label': label})
                    
                    # Add semantic context based on characteristic type
                    if char_name == 'DataVolumePostpaid5GLTE':
                        if 'GB' in label:
                            gb_amount = label.replace('GB', '').strip()
                            try:
                                gb_num = int(gb_amount)
                                if gb_num >= 50:
                                    semantic_context.append('high-data unlimited heavy-usage streaming')
                                elif gb_num >= 20:
                                    semantic_context.append('medium-high-data regular-usage')
                                elif gb_num >= 10:
                                    semantic_context.append('medium-data moderate-usage')
                                else:
                                    semantic_context.append('low-data light-usage basic')
                            except:
                                pass
                    
                    elif char_name == 'telefonie_sms':
                        if 'Flat' in label or 'unlimited' in label.lower():
                            semantic_context.append('unlimited-calls unlimited-sms all-networks')
                    
                    elif char_name == 'selectedProductOfferingTerm':
                        if '24' in label:
                            semantic_context.append('24-month contract long-term commitment')
                        elif '00' in value or 'Keine' in label:
                            semantic_context.append('no-contract flexible monthly short-term')
                    
                    elif 'roaming' in char_name.lower() or 'international' in char_name.lower():
                        semantic_context.append('international roaming travel EU-roaming')
            
            if values:
                specs[char_name] = {
                    'label': char_label,
                    'values': values,
                    'is_visible': char.get('isCustomerVisible', False),
                    'semantic_context': list(set(semantic_context))  # Remove duplicates
                }
        
        return specs
    
    def _parse_characteristics(self, characteristics: List[Dict]) -> Dict:
        """
        Parse product characteristics into structured specs
        
        Args:
            characteristics: List of characteristic dictionaries
            
        Returns:
            Dict: Parsed specifications
        """
        specs = {}
        
        for char in characteristics:
            char_name = char.get('name', '')
            char_label = char.get('label', char_name)
            char_values = char.get('characteristicValues', [])
            
            if not char_name or not char_values:
                continue
            
            # Extract values
            values = []
            for val in char_values:
                value = val.get('value', '')
                label = val.get('label', value)
                if value:
                    values.append({'value': value, 'label': label})
            
            if values:
                specs[char_name] = {
                    'label': char_label,
                    'values': values,
                    'is_visible': char.get('isCustomerVisible', False)
                }
        
        return specs
    
    def load_all_data(self) -> bool:
        """
        Load data from all sources (listing.json and tariff 1.json)
        
        Returns:
            bool: Success status
        """
        success = True
        
        # Load listing data
        if not self.load_listing_data():
            success = False
            logging.warning("Failed to load listing data")
        
        # Load tariff data
        if not self.load_tariff_data():
            success = False
            logging.warning("Failed to load tariff data")
        
        if success:
            self.initialized = True
            total_products = len(self.products) + len(self.tariff_data)
            logging.info(f"Enhanced knowledge base initialized: {total_products} total products")
        
        return success
    
    def get_enhanced_plan_context(self, plan_id: str) -> str:
        """
        Get enhanced context for a plan combining CSV data and tariff data
        
        Args:
            plan_id: Plan ID to get context for
            
        Returns:
            str: Rich context string combining multiple sources
        """
        context_parts = []
        
        # Check tariff data first (more detailed)
        if plan_id in self.tariff_data:
            tariff = self.tariff_data[plan_id]
            context = f"Plan: {tariff['name']} (ID: {plan_id})\n"
            context += f"Type: {tariff['group']} - {tariff['businessGroup']}\n"
            
            if tariff['description']:
                # Clean HTML from description
                import re
                clean_desc = re.sub('<.*?>', '', tariff['description'])
                clean_desc = clean_desc.replace('\n', ' ').replace('\r', ' ')
                context += f"Description: {clean_desc[:200]}...\n"
            
            # Add key tariff specifications
            tariff_specs = tariff['tariff_specs']
            key_features = []
            
            for spec_name, spec_data in tariff_specs.items():
                if spec_data.get('is_visible', False) and spec_data['values']:
                    label = spec_data.get('label', spec_name)
                    value = spec_data['values'][0]['label']
                    key_features.append(f"{label}: {value}")
                    
                    # Add semantic context
                    if spec_data.get('semantic_context'):
                        key_features.extend(spec_data['semantic_context'])
            
            if key_features:
                context += f"Key Features: {'; '.join(key_features[:8])}\n"
            
            context_parts.append(context)
        
        # Check basic plan data
        if plan_id in self.plan_details:
            plan = self.plan_details[plan_id]
            context = f"Additional Info: {plan['name']}\n"
            if plan['description']:
                context += f"Details: {plan['description'][:100]}...\n"
            context_parts.append(context)
        
        return "\n---\n".join(context_parts) if context_parts else f"No detailed information found for plan {plan_id}"
    
    def get_device_details(self, device_id: str) -> Optional[Dict]:
        """
        Get detailed device information
        
        Args:
            device_id: Device ID
            
        Returns:
            Dict: Device details or None if not found
        """
        return self.device_specs.get(device_id)
    
    def get_plan_details(self, plan_id: str) -> Optional[Dict]:
        """
        Get detailed plan information
        
        Args:
            plan_id: Plan ID
            
        Returns:
            Dict: Plan details or None if not found
        """
        return self.plan_details.get(plan_id)
    
    def get_product_context(self, product_ids: List[str]) -> str:
        """
        Get rich context for specific products
        
        Args:
            product_ids: List of product IDs
            
        Returns:
            str: Formatted context string
        """
        if not self.initialized:
            return ""
        
        context_parts = []
        
        for product_id in product_ids[:5]:  # Limit to 5 products
            product = self.products.get(product_id)
            if not product:
                continue
            
            # Build context string
            context = f"Product: {product['name']} (ID: {product_id})\n"
            context += f"Type: {product['group']}\n"
            
            if product['description']:
                context += f"Description: {product['description']}\n"
            
            # Add key specifications
            specs = product['specs']
            key_specs = []
            
            # Look for important specs
            for spec_name, spec_data in specs.items():
                if spec_data.get('is_visible', False) and spec_data['values']:
                    value = spec_data['values'][0]['value']
                    label = spec_data.get('label', spec_name)
                    key_specs.append(f"{label}: {value}")
            
            if key_specs:
                context += f"Key Specs: {'; '.join(key_specs[:5])}\n"  # Top 5 specs
            
            context_parts.append(context)
        
        return "\n---\n".join(context_parts)
    
    def search_products_by_feature(self, feature_query: str) -> List[str]:
        """
        Search products by feature or specification
        
        Args:
            feature_query: Feature to search for
            
        Returns:
            List[str]: List of matching product IDs
        """
        if not self.initialized:
            return []
        
        matching_products = []
        feature_lower = feature_query.lower()
        
        for product_id, product in self.products.items():
            # Search in name and description
            if (feature_lower in product['name'].lower() or 
                feature_lower in product.get('description', '').lower()):
                matching_products.append(product_id)
                continue
            
            # Search in specifications
            for spec_name, spec_data in product['specs'].items():
                if feature_lower in spec_name.lower():
                    matching_products.append(product_id)
                    break
                
                for value_data in spec_data['values']:
                    if (feature_lower in value_data['value'].lower() or
                        feature_lower in value_data['label'].lower()):
                        matching_products.append(product_id)
                        break
                else:
                    continue
                break
        
        return matching_products
    
    def get_feature_explanation(self, feature: str, product_ids: List[str]) -> str:
        """
        Get explanation of a feature across multiple products
        
        Args:
            feature: Feature name to explain
            product_ids: List of product IDs to check
            
        Returns:
            str: Feature explanation
        """
        if not self.initialized:
            return f"Information about {feature} is not available."
        
        feature_lower = feature.lower()
        explanations = []
        
        for product_id in product_ids[:3]:  # Check top 3 products
            product = self.products.get(product_id)
            if not product:
                continue
            
            # Look for feature in specs
            for spec_name, spec_data in product['specs'].items():
                if feature_lower in spec_name.lower():
                    values = [v['label'] for v in spec_data['values']]
                    explanations.append(f"{product['name']}: {spec_data['label']} - {', '.join(values)}")
                    break
        
        if explanations:
            return f"Feature '{feature}' details:\n" + "\n".join(explanations)
        else:
            return f"No detailed information found for feature '{feature}' in the selected products."

# Global knowledge base instance
knowledge_base = ProductKnowledgeBase()

def initialize_knowledge_base(listing_file: str = "listing.json", tariff_file: str = "tariff 1.json") -> bool:
    """
    Initialize the enhanced knowledge base with both listing and tariff data
    
    Args:
        listing_file: Path to listing.json file
        tariff_file: Path to tariff 1.json file
        
    Returns:
        bool: Success status
    """
    global knowledge_base
    knowledge_base = ProductKnowledgeBase(listing_file, tariff_file)
    return knowledge_base.load_all_data()

def get_product_knowledge_context(product_ids: List[str]) -> str:
    """
    Get knowledge base context for products
    
    Args:
        product_ids: List of product IDs
        
    Returns:
        str: Context string
    """
    global knowledge_base
    return knowledge_base.get_product_context(product_ids)

def get_enhanced_plan_knowledge_context(plan_ids: List[str]) -> str:
    """
    Get enhanced knowledge base context for plans using tariff data
    
    Args:
        plan_ids: List of plan IDs
        
    Returns:
        str: Enhanced context string
    """
    global knowledge_base
    context_parts = []
    
    for plan_id in plan_ids[:3]:  # Limit to top 3 plans
        context = knowledge_base.get_enhanced_plan_context(plan_id)
        if context:
            context_parts.append(context)
    
    return "\n\n===\n\n".join(context_parts)

def search_knowledge_base(query: str) -> List[str]:
    """
    Search knowledge base for products matching query
    
    Args:
        query: Search query
        
    Returns:
        List[str]: Matching product IDs
    """
    global knowledge_base
    return knowledge_base.search_products_by_feature(query)

def explain_product_feature(feature: str, product_ids: List[str]) -> str:
    """
    Explain a specific feature across products
    
    Args:
        feature: Feature to explain
        product_ids: Product IDs to check
        
    Returns:
        str: Feature explanation
    """
    global knowledge_base
    return knowledge_base.get_feature_explanation(feature, product_ids)
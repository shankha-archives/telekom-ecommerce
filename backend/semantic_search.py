"""
Semantic Search Module for RAG-enhanced Product Recommendations

This module provides semantic search capabilities using sentence transformers
to improve product matching beyond simple keyword searches.
"""

import json
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    logging.warning("sentence-transformers or faiss-cpu not available. Semantic search will be disabled.")

class SemanticProductSearch:
    """
    Semantic search engine for products using sentence transformers and FAISS.
    Provides improved product matching through semantic similarity.
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.model = None
        self.device_embeddings = None
        self.plan_embeddings = None
        self.device_index = None
        self.plan_index = None
        self.device_texts = []
        self.plan_texts = []
        self.device_ids = []
        self.plan_ids = []
        self.is_initialized = False
        
        if DEPENDENCIES_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                self.is_initialized = True
                logging.info(f"Semantic search initialized with model: {model_name}")
            except Exception as e:
                logging.error(f"Failed to initialize semantic search: {str(e)}")
                self.is_initialized = False
        else:
            logging.warning("Semantic search dependencies not available")
    
    def is_available(self) -> bool:
        """Check if semantic search is available and initialized"""
        return self.is_initialized and DEPENDENCIES_AVAILABLE
    
    def create_device_embeddings(self, devices: List[Dict]) -> bool:
        """
        Create embeddings for device data
        
        Args:
            devices: List of device dictionaries
            
        Returns:
            bool: Success status
        """
        if not self.is_available():
            return False
            
        try:
            # Extract meaningful text from devices for embedding
            self.device_texts = []
            self.device_ids = []
            
            for device in devices:
                # Combine device name, brand, description, and features
                text_parts = []
                
                # Basic info
                if device.get('name'):
                    text_parts.append(device['name'])
                if device.get('brand'):
                    text_parts.append(device['brand'])
                if device.get('description'):
                    text_parts.append(device['description'])
                
                # Features (handle both string and list formats)
                features = device.get('features', [])
                if isinstance(features, str):
                    text_parts.append(features)
                elif isinstance(features, list):
                    text_parts.extend(features)
                
                # Storage info
                if device.get('storage'):
                    text_parts.append(f"Storage: {device['storage']}")
                
                # Price range (semantic understanding of budget categories)
                price = device.get('price', 0)
                if price:
                    try:
                        price_val = float(price) if isinstance(price, str) else price
                        if price_val < 300:
                            text_parts.append("budget affordable cheap")
                        elif price_val < 600:
                            text_parts.append("mid-range moderate")
                        else:
                            text_parts.append("premium high-end expensive")
                    except:
                        pass
                
                # Combine all text parts
                device_text = " ".join(text_parts)
                self.device_texts.append(device_text)
                self.device_ids.append(device.get('id', ''))
            
            # Create embeddings
            if self.device_texts:
                self.device_embeddings = self.model.encode(self.device_texts)
                
                # Create FAISS index for fast similarity search
                dimension = self.device_embeddings.shape[1]
                self.device_index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
                
                # Normalize embeddings for cosine similarity
                faiss.normalize_L2(self.device_embeddings)
                self.device_index.add(self.device_embeddings.astype('float32'))
                
                logging.info(f"Created embeddings for {len(self.device_texts)} devices")
                return True
            
        except Exception as e:
            logging.error(f"Failed to create device embeddings: {str(e)}")
            return False
        
        return False
    
    def create_plan_embeddings(self, plans: List[Dict], tariff_data: Dict = None) -> bool:
        """
        Create enhanced embeddings for plan data using both CSV and tariff data
        
        Args:
            plans: List of plan dictionaries from CSV
            tariff_data: Dictionary of tariff data from tariff 1.json
            
        Returns:
            bool: Success status
        """
        if not self.is_available():
            return False
            
        try:
            # Extract meaningful text from plans for embedding
            self.plan_texts = []
            self.plan_ids = []
            
            for plan in plans:
                # Combine plan name, data, features, and characteristics
                text_parts = []
                
                # Basic info from CSV
                if plan.get('name'):
                    text_parts.append(plan['name'])
                if plan.get('data'):
                    text_parts.append(f"Data: {plan['data']}")
                
                # Features (handle both string and list formats)
                features = plan.get('features', [])
                if isinstance(features, str):
                    text_parts.append(features)
                elif isinstance(features, list):
                    text_parts.extend(features)
                
                # Enhanced tariff data integration
                plan_id = plan.get('id', '')
                if tariff_data and plan_id in tariff_data:
                    tariff = tariff_data[plan_id]
                    
                    # Add rich tariff description
                    if tariff.get('description'):
                        # Clean HTML and extract key terms
                        import re
                        clean_desc = re.sub('<.*?>', '', tariff['description'])
                        text_parts.append(clean_desc)
                    
                    # Add tariff specifications with semantic context
                    tariff_specs = tariff.get('tariff_specs', {})
                    for spec_name, spec_data in tariff_specs.items():
                        if spec_data.get('values'):
                            # Add specification labels and values
                            for value_data in spec_data['values']:
                                text_parts.append(value_data.get('label', ''))
                        
                        # Add semantic context
                        if spec_data.get('semantic_context'):
                            text_parts.extend(spec_data['semantic_context'])
                
                # Price-based semantic terms
                price = plan.get('price', 0)
                if price:
                    try:
                        price_val = float(price) if isinstance(price, str) else price
                        if price_val < 30:
                            text_parts.append("budget cheap affordable low-cost")
                        elif price_val < 50:
                            text_parts.append("mid-range moderate standard")
                        else:
                            text_parts.append("premium expensive unlimited high-end")
                    except:
                        pass
                
                # Data amount semantic terms (enhanced)
                data_text = plan.get('data', '').lower()
                if 'unlimited' in data_text:
                    text_parts.append("unlimited infinite no-limit high-usage streaming heavy-user")
                elif any(x in data_text for x in ['50gb', '60gb', '100gb']):
                    text_parts.append("very-high-data power-user streaming gaming")
                elif any(x in data_text for x in ['20gb', '25gb', '30gb']):
                    text_parts.append("high-data heavy-usage streaming regular-user")
                elif any(x in data_text for x in ['10gb', '15gb']):
                    text_parts.append("medium-data moderate-usage casual-user")
                elif any(x in data_text for x in ['2gb', '3gb', '5gb']):
                    text_parts.append("low-data light-usage basic minimal-user")
                
                # Contract and flexibility terms
                duration = plan.get('duration', '').lower()
                if 'month' in duration and '24' not in duration:
                    text_parts.append("flexible monthly no-commitment short-term")
                elif '24' in duration:
                    text_parts.append("24-month contract long-term commitment")
                
                # Combine all text parts and clean
                plan_text = " ".join(text_parts)
                plan_text = re.sub(r'\s+', ' ', plan_text).strip()  # Clean multiple spaces
                self.plan_texts.append(plan_text)
                self.plan_ids.append(plan_id)
            
            # Create embeddings
            if self.plan_texts:
                self.plan_embeddings = self.model.encode(self.plan_texts)
                
                # Create FAISS index for fast similarity search
                dimension = self.plan_embeddings.shape[1]
                self.plan_index = faiss.IndexFlatIP(dimension)
                
                # Normalize embeddings for cosine similarity
                faiss.normalize_L2(self.plan_embeddings)
                self.plan_index.add(self.plan_embeddings.astype('float32'))
                
                logging.info(f"Created enhanced embeddings for {len(self.plan_texts)} plans with tariff data")
                return True
            
        except Exception as e:
            logging.error(f"Failed to create enhanced plan embeddings: {str(e)}")
            return False
        
        return False
    
    def semantic_search_devices(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Perform semantic search on devices
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of (device_id, similarity_score) tuples
        """
        if not self.is_available() or self.device_index is None:
            return []
        
        try:
            # Encode query
            query_embedding = self.model.encode([query])
            faiss.normalize_L2(query_embedding)
            
            # Search
            scores, indices = self.device_index.search(query_embedding.astype('float32'), min(top_k, len(self.device_ids)))
            
            # Return results
            results = []
            for i, (idx, score) in enumerate(zip(indices[0], scores[0])):
                if idx < len(self.device_ids) and score > 0.3:  # Threshold for relevance
                    results.append((self.device_ids[idx], float(score)))
            
            return results
            
        except Exception as e:
            logging.error(f"Error in semantic device search: {str(e)}")
            return []
    
    def semantic_search_plans(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Perform semantic search on plans
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of (plan_id, similarity_score) tuples
        """
        if not self.is_available() or self.plan_index is None:
            return []
        
        try:
            # Encode query
            query_embedding = self.model.encode([query])
            faiss.normalize_L2(query_embedding)
            
            # Search
            scores, indices = self.plan_index.search(query_embedding.astype('float32'), min(top_k, len(self.plan_ids)))
            
            # Return results
            results = []
            for i, (idx, score) in enumerate(zip(indices[0], scores[0])):
                if idx < len(self.plan_ids) and score > 0.3:  # Threshold for relevance
                    results.append((self.plan_ids[idx], float(score)))
            
            return results
            
        except Exception as e:
            logging.error(f"Error in semantic plan search: {str(e)}")
            return []
    
    def get_device_context(self, device_ids: List[str]) -> str:
        """
        Get rich context for specific devices for RAG
        
        Args:
            device_ids: List of device IDs
            
        Returns:
            Formatted context string
        """
        if not device_ids:
            return ""
        
        context_parts = []
        for device_id in device_ids[:3]:  # Limit to top 3 for context
            if device_id in self.device_ids:
                idx = self.device_ids.index(device_id)
                if idx < len(self.device_texts):
                    context_parts.append(f"Device {device_id}: {self.device_texts[idx]}")
        
        return "\n".join(context_parts)
    
    def get_plan_context(self, plan_ids: List[str]) -> str:
        """
        Get rich context for specific plans for RAG
        
        Args:
            plan_ids: List of plan IDs
            
        Returns:
            Formatted context string
        """
        if not plan_ids:
            return ""
        
        context_parts = []
        for plan_id in plan_ids[:3]:  # Limit to top 3 for context
            if plan_id in self.plan_ids:
                idx = self.plan_ids.index(plan_id)
                if idx < len(self.plan_texts):
                    context_parts.append(f"Plan {plan_id}: {self.plan_texts[idx]}")
        
        return "\n".join(context_parts)

# Global instance
semantic_search = SemanticProductSearch()

def initialize_semantic_search(devices: List[Dict], plans: List[Dict], tariff_data: Dict = None) -> bool:
    """
    Initialize enhanced semantic search with product data and tariff data
    
    Args:
        devices: List of device dictionaries
        plans: List of plan dictionaries
        tariff_data: Dictionary of tariff data from tariff 1.json
        
    Returns:
        bool: Success status
    """
    global semantic_search
    
    if not semantic_search.is_available():
        logging.warning("Semantic search not available, skipping initialization")
        return False
    
    success = True
    
    # Initialize device embeddings
    if devices:
        success &= semantic_search.create_device_embeddings(devices)
    
    # Initialize enhanced plan embeddings with tariff data
    if plans:
        success &= semantic_search.create_plan_embeddings(plans, tariff_data)
    
    return success

def semantic_search_products(query: str, product_type: str = "both") -> Dict[str, List[Tuple[str, float]]]:
    """
    Perform semantic search on products
    
    Args:
        query: Search query
        product_type: "devices", "plans", or "both"
        
    Returns:
        Dictionary with search results
    """
    global semantic_search
    
    results = {"devices": [], "plans": []}
    
    if not semantic_search.is_available():
        return results
    
    if product_type in ["devices", "both"]:
        results["devices"] = semantic_search.semantic_search_devices(query)
    
    if product_type in ["plans", "both"]:
        results["plans"] = semantic_search.semantic_search_plans(query)
    
    return results
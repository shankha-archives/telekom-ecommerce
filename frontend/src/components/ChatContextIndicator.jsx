import React, { useState } from 'react';
import { Info, ChevronDown, ChevronUp, Users, Database, Clock, Filter } from 'lucide-react';

/**
 * ChatContextIndicator Component
 * 
 * Displays a summary of the user's context that the AI assistant is aware of,
 * including preferences, conversation history, and recent views.
 * 
 * @param {Object} session - Session data with user preferences and history
 */
const ChatContextIndicator = ({ session }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!session) {
    return null;
  }

  // Count significant context items
  const contextItems = [];

  // Add device preferences to context items
  const devicePreferences = session?.user_preferences?.device_preferences || {};
  if (devicePreferences.brand?.length > 0) {
    contextItems.push({
      type: 'brand',
      text: `Brand: ${devicePreferences.brand.join(', ')}`,
      icon: <Filter className="w-3 h-3 text-blue-600" />
    });
  }

  if (devicePreferences.price_range) {
    const range = devicePreferences.price_range;
    contextItems.push({
      type: 'price',
      text: `Budget: €${range.min}-${range.max}`,
      icon: <Filter className="w-3 h-3 text-blue-600" />
    });
  }

  if (devicePreferences.storage?.length > 0) {
    contextItems.push({
      type: 'storage',
      text: `Storage: ${devicePreferences.storage.join(', ')}`,
      icon: <Database className="w-3 h-3 text-blue-600" />
    });
  }

  if (devicePreferences.color?.length > 0) {
    contextItems.push({
      type: 'color',
      text: `Color: ${devicePreferences.color.join(', ')}`,
      icon: <Filter className="w-3 h-3 text-blue-600" />
    });
  }

  // Add plan preferences to context items
  const planPreferences = session?.user_preferences?.plan_preferences || {};
  if (planPreferences.data_needs) {
    const dataMap = {
      'low': 'Low data usage',
      'medium': 'Medium data usage',
      'high': 'High data usage'
    };
    contextItems.push({
      type: 'data',
      text: dataMap[planPreferences.data_needs] || planPreferences.data_needs,
      icon: <Database className="w-3 h-3 text-indigo-600" />
    });
  }

  if (planPreferences.price_sensitivity) {
    const priceMap = {
      'low': 'Budget conscious',
      'medium': 'Mid-range budget',
      'high': 'Premium budget'
    };
    contextItems.push({
      type: 'price',
      text: priceMap[planPreferences.price_sensitivity] || planPreferences.price_sensitivity,
      icon: <Filter className="w-3 h-3 text-indigo-600" />
    });
  }

  if (planPreferences.international) {
    contextItems.push({
      type: 'international',
      text: 'Needs international features',
      icon: <Users className="w-3 h-3 text-indigo-600" />
    });
  }

  if (planPreferences.family_plan) {
    contextItems.push({
      type: 'family',
      text: 'Interested in family plans',
      icon: <Users className="w-3 h-3 text-indigo-600" />
    });
  }

  // Add recent views context
  const recentDevices = session?.recently_viewed?.devices || [];
  if (recentDevices.length > 0) {
    contextItems.push({
      type: 'recent',
      text: `Recently viewed: ${recentDevices.map(d => d.name).join(', ')}`,
      icon: <Clock className="w-3 h-3 text-gray-600" />
    });
  }

  // If we have no context, return nothing
  if (contextItems.length === 0) {
    return null;
  }

  return (
    <div className="px-4 py-2 border-b bg-gray-50">
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-blue-500" />
          <span className="text-xs font-medium text-gray-600">
            {isExpanded ? 'Current preferences:' : `${contextItems.length} preferences understood`}
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-gray-500" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-500" />
        )}
      </div>
      
      {isExpanded && (
        <div className="mt-2 pl-6 space-y-1">
          {contextItems.map((item, idx) => (
            <div key={idx} className="flex items-center gap-2 py-1">
              {item.icon}
              <span className="text-xs text-gray-600">{item.text}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ChatContextIndicator;
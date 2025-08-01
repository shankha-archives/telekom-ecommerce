import React from 'react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Card, CardContent } from './ui/card';
import { Info, Check, X, ThumbsUp, ThumbsDown } from 'lucide-react';

/**
 * Enhanced Chat Message Component
 * 
 * Supports multiple message types:
 * - 'user': Messages from the user
 * - 'assistant': Messages from the AI assistant
 * - 'results': Search results with devices and plans
 * - 'preferences': User preference summaries
 * - 'comparison': Product comparison views
 */
const EnhancedChatMessage = ({ message, onActionClick, explanations = {} }) => {
  // Handler for suggested question clicks
  const handleSuggestionClick = (question) => {
    if (onActionClick) {
      onActionClick(question);
    }
  };

  // Handle user feedback
  const handleFeedback = (isPositive) => {
    // This could send feedback to the backend
    console.log(`User gave ${isPositive ? 'positive' : 'negative'} feedback for message:`, message.id);
  };

  // Message type: Results (device and plan recommendations)
  if (message.type === 'results') {
    return (
      <div className="mb-4">
        {message.devices && message.devices.length > 0 && (
          <div className="mb-4">
            <h4 className="font-semibold mb-2 text-gray-700">📱 Recommended Devices:</h4>
            <div className="grid gap-3">
              {message.devices.map((device) => (
                <EnhancedDeviceCard 
                  key={device.id} 
                  device={device} 
                  showInChat={true}
                  explanation={explanations?.device_explanations?.[device.id] || []} 
                />
              ))}
            </div>
          </div>
        )}
        
        {message.plans && message.plans.length > 0 && (
          <div>
            <h4 className="font-semibold mb-2 text-gray-700">📋 Recommended Plans:</h4>
            <div className="grid gap-3">
              {message.plans.map((plan) => (
                <EnhancedPlanCard 
                  key={plan.id} 
                  plan={plan} 
                  showInChat={true} 
                  explanation={explanations?.plan_explanations?.[plan.id] || []}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }
  
  // Message type: Preferences
  if (message.type === 'preferences') {
    return (
      <div className="flex justify-start mb-3">
        <div className="w-full px-4 py-3 rounded-2xl shadow-sm bg-blue-50 border border-blue-100 text-gray-800">
          <div className="flex items-center mb-2">
            <Info className="w-4 h-4 text-blue-500 mr-2" />
            <h4 className="font-medium text-blue-800">I understand your preferences:</h4>
          </div>
          
          <div className="grid grid-cols-1 gap-2 mt-3">
            {message.preferences?.map((pref, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0"></div>
                <p className="text-sm text-gray-700">{pref}</p>
              </div>
            ))}
          </div>
          
          <div className="mt-3 text-right">
            <Button 
              onClick={() => onActionClick('edit_preferences')}
              variant="ghost"
              size="sm"
              className="text-xs text-blue-600 hover:text-blue-800"
            >
              Edit preferences
            </Button>
          </div>
        </div>
      </div>
    );
  }
  
  // Message type: Comparison
  if (message.type === 'comparison') {
    return (
      <div className="w-full mb-4 overflow-x-auto">
        <Card className="bg-white border rounded-xl p-4">
          <h4 className="font-semibold mb-3 text-gray-700">Product Comparison:</h4>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px]">
              <thead>
                <tr className="border-b">
                  <th className="py-2 px-3 text-left">Feature</th>
                  {message.items?.map(item => (
                    <th key={item.id} className="py-2 px-3 text-left">{item.name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {message.comparisonPoints?.map((point, idx) => (
                  <tr key={idx} className={idx % 2 === 0 ? 'bg-gray-50' : ''}>
                    <td className="py-2 px-3 font-medium">{point.feature}</td>
                    {message.items?.map(item => (
                      <td key={`${item.id}-${idx}`} className="py-2 px-3">
                        {point.values[item.id]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    );
  }
  
  // Default message types: user and assistant
  return (
    <div className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} mb-3 group`}>
      <div 
        className={`max-w-xs lg:max-w-md px-4 py-3 rounded-2xl shadow-sm transition-all ${
          message.type === 'user' 
            ? 'bg-magenta-600 text-white rounded-br-md' 
            : 'bg-white border text-gray-800 rounded-bl-md'
        }`}
      >
        <p className="text-sm leading-relaxed">{message.message}</p>
        
        {/* Show follow-up questions for assistant messages */}
        {message.type === 'assistant' && message.follow_up_questions && message.follow_up_questions.length > 0 && (
          <div className="mt-3 flex flex-col gap-2">
            {message.follow_up_questions.map((question, idx) => (
              <Button 
                key={idx}
                onClick={() => handleSuggestionClick(question)}
                className="text-xs text-left px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-xl text-gray-700 transition-colors justify-start"
                variant="ghost"
                size="sm"
              >
                {question}
              </Button>
            ))}
          </div>
        )}
        
        <div className="flex items-center justify-between">
          <span className="text-xs opacity-70 mt-1">
            {new Date(message.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
          </span>
          
          {/* Feedback buttons for assistant messages */}
          {message.type === 'assistant' && (
            <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-2 mt-1">
              <Button 
                onClick={() => handleFeedback(true)} 
                variant="ghost" 
                size="sm"
                className="p-0 h-5 w-5 text-gray-400 hover:text-green-500"
              >
                <ThumbsUp className="w-3 h-3" />
              </Button>
              <Button 
                onClick={() => handleFeedback(false)} 
                variant="ghost" 
                size="sm"
                className="p-0 h-5 w-5 text-gray-400 hover:text-red-500"
              >
                <ThumbsDown className="w-3 h-3" />
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Enhanced Device Card with Explanations
const EnhancedDeviceCard = ({ device, showInChat = false, explanation = [] }) => (
  <Card className={`group hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 bg-white/90 backdrop-blur-sm border-0 shadow-lg ${showInChat ? 'mb-4' : ''}`}>
    <CardContent className="p-4">
      <div className="flex items-start gap-3">
        {/* Device image */}
        <div className="w-16 h-16 flex-shrink-0 overflow-hidden rounded-md">
          <img 
            src={device.image} 
            alt={device.name}
            className="w-full h-full object-cover"
            onError={(e) => {
              e.target.src = 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60';
            }}
          />
        </div>
        
        {/* Device info */}
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1">
            <h3 className="font-bold text-gray-900">{device.name}</h3>
            <div className="text-lg font-bold text-magenta-600">€{device.price}</div>
          </div>
          
          <p className="text-xs text-gray-600">{device.brand} • {device.storage} • {device.color}</p>
          
          {/* Explanation badges */}
          {explanation && explanation.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {explanation.map((item, idx) => (
                <Badge key={idx} variant="secondary" className="text-xs bg-blue-50 text-blue-700 hover:bg-blue-100">
                  <Check className="w-3 h-3 mr-1" /> {item}
                </Badge>
              ))}
            </div>
          )}
          
          <div className="mt-2">
            <Button 
              className="bg-magenta-600 hover:bg-magenta-700 text-white px-3 py-1 rounded-lg transition-colors text-xs"
              size={showInChat ? "sm" : "default"}
            >
              Add to Cart
            </Button>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
);

// Enhanced Plan Card with Explanations
const EnhancedPlanCard = ({ plan, showInChat = false, explanation = [] }) => (
  <Card className={`relative transition-all duration-300 hover:shadow-xl ${plan.popular ? 'ring-1 ring-magenta-500' : ''} bg-white/90 backdrop-blur-sm border-0 shadow-lg ${showInChat ? 'mb-4' : ''}`}>
    <CardContent className="p-4">
      <div className="flex items-start gap-3">
        {/* Plan info */}
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1">
            <h3 className="font-bold text-gray-900">{plan.name}</h3>
            <div className="text-lg font-bold text-magenta-600">€{plan.price}</div>
          </div>
          
          <p className="text-xs text-gray-600">
            {plan.data} • {plan.duration} • {plan.minutes} minutes
          </p>
          
          {/* Main features */}
          <div className="mt-2 text-sm">
            {plan.features && plan.features.slice(0, 2).map((feature, idx) => (
              <div key={idx} className="flex items-center gap-1">
                <Check className="w-3 h-3 text-green-500" />
                <span className="text-xs">{feature}</span>
              </div>
            ))}
            {plan.features && plan.features.length > 2 && (
              <div className="text-xs text-gray-500">+{plan.features.length - 2} more features</div>
            )}
          </div>
          
          {/* Explanation badges */}
          {explanation && explanation.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {explanation.map((item, idx) => (
                <Badge key={idx} variant="secondary" className="text-xs bg-blue-50 text-blue-700 hover:bg-blue-100">
                  <Check className="w-3 h-3 mr-1" /> {item}
                </Badge>
              ))}
            </div>
          )}
          
          <div className="mt-2">
            <Button 
              className="bg-magenta-600 hover:bg-magenta-700 text-white px-3 py-1 rounded-lg transition-colors text-xs"
              size={showInChat ? "sm" : "default"}
            >
              Choose Plan
            </Button>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
);

export default EnhancedChatMessage;
import React, { useState, useEffect } from 'react';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { CheckCircle, AlertTriangle, Zap, Package, Euro } from 'lucide-react';
import AddToCartButton from './AddToCartButton';

const BundleCard = ({ device, plan, sessionId, onCartUpdate, showCompatibilityCheck = true, apiBaseUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001' }) => {
  const [compatibility, setCompatibility] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (showCompatibilityCheck && device?.id && plan?.id) {
      checkCompatibility();
    }
  }, [device?.id, plan?.id]);

  const checkCompatibility = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${apiBaseUrl}/api/cart/compatibility-check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: device.id,
          plan_id: plan.id
        })
      });

      const result = await response.json();
      setCompatibility(result);
    } catch (error) {
      console.error('Compatibility check failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const calculateBundlePrice = () => {
    const devicePrice = parseFloat(device?.price || 0);
    const planPrice = parseFloat(plan?.price || 0);
    const totalPrice = devicePrice + planPrice;
    
    // Calculate bundle savings (5% discount for bundles)
    const bundleDiscount = totalPrice * 0.05;
    const bundlePrice = totalPrice - bundleDiscount;
    
    return {
      originalPrice: totalPrice,
      bundlePrice: bundlePrice,
      savings: bundleDiscount
    };
  };

  const pricing = calculateBundlePrice();

  // Create bundle object for cart
  const bundleItem = {
    id: `bundle_${device?.id}_${plan?.id}`,
    name: `${device?.name} + ${plan?.name}`,
    price: pricing.bundlePrice,
    original_price: pricing.originalPrice,
    bundle_components: [
      {
        type: 'device',
        id: device?.id,
        name: device?.name,
        price: device?.price
      },
      {
        type: 'plan',
        id: plan?.id,
        name: plan?.name,
        price: plan?.price
      }
    ]
  };

  return (
    <Card className="group hover:shadow-xl transition-all duration-300 bg-gradient-to-br from-blue-50 to-purple-50 border-0 shadow-lg">
      <CardContent className="p-6">
        {/* Bundle Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Package className="w-5 h-5 text-blue-600" />
            <h3 className="font-bold text-lg text-gray-900">Perfect Bundle</h3>
            <Badge className="bg-green-100 text-green-800">Save €{pricing.savings.toFixed(2)}</Badge>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-500 line-through">€{pricing.originalPrice.toFixed(2)}</div>
            <div className="text-2xl font-bold text-blue-600">€{pricing.bundlePrice.toFixed(2)}</div>
          </div>
        </div>

        {/* Bundle Components */}
        <div className="space-y-3 mb-4">
          {/* Device Component */}
          <div className="flex items-center gap-3 p-3 bg-white rounded-lg border">
            <div className="w-12 h-12 flex-shrink-0 overflow-hidden rounded-md">
              <img 
                src={device?.image} 
                alt={device?.name}
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.target.src = '/api/placeholder/48/48';
                }}
              />
            </div>
            <div className="flex-1">
              <h4 className="font-medium text-sm">{device?.name}</h4>
              <p className="text-xs text-gray-500">{device?.brand} • {device?.storage} • {device?.color}</p>
            </div>
            <div className="text-sm font-semibold">€{device?.price}</div>
          </div>

          {/* Plan Component */}
          <div className="flex items-center gap-3 p-3 bg-white rounded-lg border">
            <div className="w-12 h-12 flex-shrink-0 bg-gradient-to-br from-purple-500 to-blue-500 rounded-md flex items-center justify-center">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <div className="flex-1">
              <h4 className="font-medium text-sm">{plan?.name}</h4>
              <p className="text-xs text-gray-500">{plan?.data} • {plan?.duration} • {plan?.minutes} minutes</p>
            </div>
            <div className="text-sm font-semibold">€{plan?.price}</div>
          </div>
        </div>

        {/* Compatibility Check */}
        {compatibility && (
          <div className="mb-4 p-3 bg-white rounded-lg border">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span className="text-sm font-medium">Compatibility Check</span>
            </div>
            
            {compatibility.warnings && compatibility.warnings.length > 0 && (
              <div className="space-y-1 mb-2">
                {compatibility.warnings.map((warning, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-xs text-orange-600">
                    <AlertTriangle className="w-3 h-3" />
                    <span>{warning}</span>
                  </div>
                ))}
              </div>
            )}
            
            {compatibility.recommendations && compatibility.recommendations.length > 0 && (
              <div className="space-y-1">
                {compatibility.recommendations.map((rec, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-xs text-blue-600">
                    <CheckCircle className="w-3 h-3" />
                    <span>{rec}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Bundle Benefits */}
        <div className="mb-4 p-3 bg-gradient-to-r from-green-50 to-blue-50 rounded-lg">
          <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
            <Euro className="w-4 h-4 text-green-600" />
            Bundle Benefits
          </h4>
          <div className="space-y-1 text-xs">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-3 h-3 text-green-500" />
              <span>Save €{pricing.savings.toFixed(2)} compared to buying separately</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="w-3 h-3 text-green-500" />
              <span>Device & plan perfectly matched</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="w-3 h-3 text-green-500" />
              <span>Single activation process</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="w-3 h-3 text-green-500" />
              <span>Priority customer support</span>
            </div>
          </div>
        </div>

        {/* Add to Cart Button */}
        <AddToCartButton
          item={bundleItem}
          itemType="bundle"
          sessionId={sessionId}
          onCartUpdate={onCartUpdate}
          apiBaseUrl={apiBaseUrl}
          className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium py-3"
        >
          <Package className="w-4 h-4 mr-2" />
          Add Bundle to Cart
        </AddToCartButton>

        {/* Individual Add Buttons */}
        <div className="flex gap-2 mt-2">
          <AddToCartButton
            item={device}
            itemType="device"
            sessionId={sessionId}
            onCartUpdate={onCartUpdate}
            apiBaseUrl={apiBaseUrl}
            variant="outline"
            size="sm"
            className="flex-1 text-xs"
          >
            Device Only
          </AddToCartButton>
          <AddToCartButton
            item={plan}
            itemType="plan"
            sessionId={sessionId}
            onCartUpdate={onCartUpdate}
            apiBaseUrl={apiBaseUrl}
            variant="outline"
            size="sm"
            className="flex-1 text-xs"
          >
            Plan Only
          </AddToCartButton>
        </div>
      </CardContent>
    </Card>
  );
};

export default BundleCard;
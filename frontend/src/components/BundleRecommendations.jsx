import React, { useState, useEffect } from 'react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Package, TrendingUp, Zap, Euro } from 'lucide-react';
import BundleCard from './BundleCard';

const BundleRecommendations = ({ sessionId, onCartUpdate, apiBaseUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001' }) => {
  const [cart, setCart] = useState([]);
  const [bundleRecommendations, setBundleRecommendations] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (sessionId) {
      fetchCartAndRecommendations();
    }
  }, [sessionId]);

  const fetchCartAndRecommendations = async () => {
    try {
      setLoading(true);
      
      // Fetch current cart
      const cartResponse = await fetch(`${apiBaseUrl}/api/cart/${sessionId}`);
      const cartData = await cartResponse.json();
      setCart(cartData);
      
      // Generate bundle recommendations based on cart contents
      const recommendations = generateBundleRecommendations(cartData.cart || []);
      setBundleRecommendations(recommendations);
      
    } catch (error) {
      console.error('Failed to fetch cart and recommendations:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateBundleRecommendations = (cartItems) => {
    const recommendations = [];
    
    // Get devices and plans from cart
    const devices = cartItems.filter(item => item.type === 'device');
    const plans = cartItems.filter(item => item.type === 'plan');
    
    // If user has devices but no plans, recommend plans
    if (devices.length > 0 && plans.length === 0) {
      // Mock recommended plans - in real app, this would come from API
      const recommendedPlans = [
        {
          id: 'MF_17249',
          name: 'MagentaMobil Basic',
          price: 24.95,
          data: '5GB',
          duration: 'monthly',
          minutes: 'unlimited',
          features: ['EU roaming', '5G', 'HotSpot Flat', 'VoLTE', 'Wi-Fi Calling']
        },
        {
          id: 'MF_17251',
          name: 'MagentaMobil Basic mit Smartphone',
          price: 34.95,
          data: '5GB',
          duration: 'monthly',
          minutes: 'unlimited',
          features: ['EU roaming', '5G', 'HotSpot Flat', 'VoLTE', 'Wi-Fi Calling']
        }
      ];
      
      devices.forEach(device => {
        recommendedPlans.forEach(plan => {
          recommendations.push({
            type: 'device_plan_bundle',
            device,
            plan,
            savings: calculateBundleSavings(device.price, plan.price),
            compatibility: 'high' // Mock compatibility
          });
        });
      });
    }
    
    // If user has plans but no devices, recommend devices
    if (plans.length > 0 && devices.length === 0) {
      // Mock recommended devices - in real app, this would come from API
      const recommendedDevices = [
        {
          id: 'MF_10001',
          name: 'Samsung Galaxy S24',
          brand: 'Samsung',
          price: 849.0,
          storage: '256GB',
          color: 'Phantom Black',
          image: '/images/devices/samsung/galaxy-s24.jpg'
        },
        {
          id: 'MF_10016',
          name: 'Apple iPhone 16',
          brand: 'Apple',
          price: 949.0,
          storage: '128GB',
          color: 'Pink',
          image: '/images/devices/apple/iphone-16.jpg'
        }
      ];
      
      plans.forEach(plan => {
        recommendedDevices.forEach(device => {
          recommendations.push({
            type: 'plan_device_bundle',
            device,
            plan,
            savings: calculateBundleSavings(device.price, plan.price),
            compatibility: 'high' // Mock compatibility
          });
        });
      });
    }
    
    // If user has both but no bundles, suggest bundle optimization
    if (devices.length > 0 && plans.length > 0) {
      // Check if any items are already bundled
      const hasBundles = cartItems.some(item => item.type === 'bundle');
      
      if (!hasBundles) {
        // Suggest bundling existing items
        devices.forEach(device => {
          plans.forEach(plan => {
            recommendations.push({
              type: 'optimize_existing',
              device,
              plan,
              savings: calculateBundleSavings(device.price, plan.price),
              compatibility: 'high',
              message: 'Bundle your current items for extra savings!'
            });
          });
        });
      }
    }
    
    return recommendations.slice(0, 3); // Limit to 3 recommendations
  };

  const calculateBundleSavings = (devicePrice, planPrice) => {
    const totalPrice = parseFloat(devicePrice) + parseFloat(planPrice);
    return totalPrice * 0.05; // 5% bundle discount
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (bundleRecommendations.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp className="w-5 h-5 text-blue-600" />
        <h3 className="font-semibold text-lg">Smart Bundle Recommendations</h3>
        <Badge className="bg-green-100 text-green-800">Save More</Badge>
      </div>
      
      <div className="space-y-4">
        {bundleRecommendations.map((rec, index) => (
          <div key={index}>
            {rec.type === 'optimize_existing' && (
              <Card className="mb-4 bg-gradient-to-r from-yellow-50 to-orange-50 border-yellow-200">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Package className="w-4 h-4 text-orange-600" />
                    <span className="font-medium text-orange-800">Bundle Optimization</span>
                  </div>
                  <p className="text-sm text-orange-700 mb-2">{rec.message}</p>
                  <p className="text-xs text-orange-600">
                    Save €{rec.savings.toFixed(2)} by bundling {rec.device.name} with {rec.plan.name}
                  </p>
                </CardContent>
              </Card>
            )}
            
            <BundleCard
              device={rec.device}
              plan={rec.plan}
              sessionId={sessionId}
              onCartUpdate={onCartUpdate}
              apiBaseUrl={apiBaseUrl}
              showCompatibilityCheck={true}
            />
          </div>
        ))}
      </div>
      
      <Card className="bg-gradient-to-r from-blue-50 to-purple-50 border-blue-200">
        <CardContent className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-blue-600" />
            <span className="font-medium text-blue-800">Why Bundle?</span>
          </div>
          <div className="space-y-1 text-sm text-blue-700">
            <div className="flex items-center gap-2">
              <Euro className="w-3 h-3" />
              <span>Save up to 10% compared to individual purchases</span>
            </div>
            <div className="flex items-center gap-2">
              <Package className="w-3 h-3" />
              <span>Guaranteed compatibility between device and plan</span>
            </div>
            <div className="flex items-center gap-2">
              <Zap className="w-3 h-3" />
              <span>Single activation process with priority support</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default BundleRecommendations;
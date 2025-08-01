import React, { useState, useEffect } from 'react';
import { Settings, X, Check } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from './ui/dialog';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Slider } from './ui/slider';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Switch } from './ui/switch';
import { Label } from './ui/label';

const UserPreferenceManager = ({ 
  sessionId, 
  preferences = {}, 
  onUpdate,
  apiBaseUrl = 'http://localhost:8001'
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('devices');
  const [devicePrefs, setDevicePrefs] = useState({
    brand: [],
    price_range: { min: 100, max: 1200 },
    storage: [],
    color: [],
    features: []
  });
  const [planPrefs, setPlanPrefs] = useState({
    data_needs: '',
    price_sensitivity: '',
    international: false,
    family_plan: false,
    contract_length: ''
  });

  // Options for UI selection
  const brandOptions = ['Apple', 'Samsung', 'Google', 'Xiaomi', 'OnePlus', 'Motorola', 'Nokia'];
  const storageOptions = ['64GB', '128GB', '256GB', '512GB', '1TB'];
  const colorOptions = ['Black', 'White', 'Blue', 'Red', 'Gold', 'Green', 'Purple'];
  const featureOptions = ['Good camera', 'Long battery life', '5G', 'Water resistant', 'Fast charging'];
  const dataNeedsOptions = ['low', 'medium', 'high'];
  const priceSensitivityOptions = ['low', 'medium', 'high'];
  const contractLengthOptions = ['monthly', '1-year', '2-year'];

  // Load preferences when component mounts or preferences prop changes
  useEffect(() => {
    if (preferences) {
      if (preferences.device_preferences) {
        setDevicePrefs({
          brand: preferences.device_preferences.brand || [],
          price_range: preferences.device_preferences.price_range || { min: 100, max: 1200 },
          storage: preferences.device_preferences.storage || [],
          color: preferences.device_preferences.color || [],
          features: preferences.device_preferences.features || []
        });
      }

      if (preferences.plan_preferences) {
        setPlanPrefs({
          data_needs: preferences.plan_preferences.data_needs || '',
          price_sensitivity: preferences.plan_preferences.price_sensitivity || '',
          international: preferences.plan_preferences.international || false,
          family_plan: preferences.plan_preferences.family_plan || false,
          contract_length: preferences.plan_preferences.contract_length || ''
        });
      }
    }
  }, [preferences]);

  // Toggle selection of array items (brands, colors, storage, etc.)
  const toggleSelection = (category, item) => {
    if (category === 'brand' || category === 'storage' || category === 'color' || category === 'features') {
      setDevicePrefs(prev => {
        const currentItems = prev[category] || [];
        return {
          ...prev,
          [category]: currentItems.includes(item)
            ? currentItems.filter(i => i !== item)
            : [...currentItems, item]
        };
      });
    }
  };

  // Set single value preferences
  const setSinglePreference = (category, value) => {
    if (['data_needs', 'price_sensitivity', 'contract_length'].includes(category)) {
      setPlanPrefs(prev => ({ ...prev, [category]: value }));
    } else if (['international', 'family_plan'].includes(category)) {
      setPlanPrefs(prev => ({ ...prev, [category]: value }));
    }
  };

  // Handle price range change
  const handlePriceRangeChange = (values) => {
    setDevicePrefs(prev => ({
      ...prev,
      price_range: {
        min: values[0],
        max: values[1]
      }
    }));
  };

  // Save preferences to backend
  const handleSave = async () => {
    // Skip if no session ID
    if (!sessionId) {
      console.warn('No session ID provided, cannot save preferences');
      setIsOpen(false);
      return;
    }

    try {
      const updatedPreferences = {
        device_preferences: devicePrefs,
        plan_preferences: planPrefs
      };

      const response = await fetch(`${apiBaseUrl}/api/session/${sessionId}/preferences`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preferences: updatedPreferences })
      });

      if (!response.ok) {
        throw new Error(`Failed to update preferences: ${response.status}`);
      }

      const result = await response.json();
      console.log('Preferences updated successfully:', result);
      
      // Call the onUpdate callback with the updated preferences
      if (onUpdate) {
        onUpdate(updatedPreferences);
      }

      setIsOpen(false);
    } catch (error) {
      console.error('Error saving preferences:', error);
    }
  };

  // Render the trigger button when dialog is closed
  if (!isOpen) {
    return (
      <Button 
        variant="outline" 
        size="sm"
        className="bg-white text-gray-700 border-gray-200 hover:bg-gray-100 flex items-center gap-1"
        onClick={() => setIsOpen(true)}
      >
        <Settings className="w-4 h-4" />
        <span className="hidden sm:inline">Preferences</span>
      </Button>
    );
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogContent className="max-w-md max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Your Preferences</DialogTitle>
          <DialogDescription>
            Customize your preferences to get more personalized recommendations
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-4">
          <TabsList className="w-full">
            <TabsTrigger value="devices" className="flex-1">Devices</TabsTrigger>
            <TabsTrigger value="plans" className="flex-1">Plans</TabsTrigger>
          </TabsList>
          
          {/* Device Preferences Tab */}
          <TabsContent value="devices" className="pt-4 space-y-6">
            {/* Brand Selection */}
            <div>
              <h3 className="text-sm font-medium mb-2">Preferred Brands</h3>
              <div className="flex flex-wrap gap-2">
                {brandOptions.map(brand => (
                  <Badge 
                    key={brand}
                    variant={devicePrefs.brand?.includes(brand) ? "default" : "outline"}
                    className="cursor-pointer transition-colors"
                    onClick={() => toggleSelection('brand', brand)}
                  >
                    {devicePrefs.brand?.includes(brand) && <Check className="w-3 h-3 mr-1" />}
                    {brand}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Price Range */}
            <div>
              <h3 className="text-sm font-medium mb-2">Price Range</h3>
              <div className="px-2">
                <Slider 
                  value={[devicePrefs.price_range?.min || 100, devicePrefs.price_range?.max || 1200]} 
                  min={0} 
                  max={2000} 
                  step={50}
                  onValueChange={handlePriceRangeChange}
                  className="mt-6"
                />
                <div className="flex justify-between mt-2">
                  <span className="text-xs">€{devicePrefs.price_range?.min || 100}</span>
                  <span className="text-xs">€{devicePrefs.price_range?.max || 1200}</span>
                </div>
              </div>
            </div>

            {/* Storage Options */}
            <div>
              <h3 className="text-sm font-medium mb-2">Storage</h3>
              <div className="flex flex-wrap gap-2">
                {storageOptions.map(storage => (
                  <Badge 
                    key={storage}
                    variant={devicePrefs.storage?.includes(storage) ? "default" : "outline"}
                    className="cursor-pointer transition-colors"
                    onClick={() => toggleSelection('storage', storage)}
                  >
                    {devicePrefs.storage?.includes(storage) && <Check className="w-3 h-3 mr-1" />}
                    {storage}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Color Options */}
            <div>
              <h3 className="text-sm font-medium mb-2">Color</h3>
              <div className="flex flex-wrap gap-2">
                {colorOptions.map(color => (
                  <Badge 
                    key={color}
                    variant={devicePrefs.color?.includes(color) ? "default" : "outline"}
                    className="cursor-pointer transition-colors"
                    onClick={() => toggleSelection('color', color)}
                  >
                    {devicePrefs.color?.includes(color) && <Check className="w-3 h-3 mr-1" />}
                    {color}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Features */}
            <div>
              <h3 className="text-sm font-medium mb-2">Important Features</h3>
              <div className="flex flex-wrap gap-2">
                {featureOptions.map(feature => (
                  <Badge 
                    key={feature}
                    variant={devicePrefs.features?.includes(feature) ? "default" : "outline"}
                    className="cursor-pointer transition-colors"
                    onClick={() => toggleSelection('features', feature)}
                  >
                    {devicePrefs.features?.includes(feature) && <Check className="w-3 h-3 mr-1" />}
                    {feature}
                  </Badge>
                ))}
              </div>
            </div>
          </TabsContent>
          
          {/* Plan Preferences Tab */}
          <TabsContent value="plans" className="pt-4 space-y-6">
            {/* Data Needs */}
            <div>
              <h3 className="text-sm font-medium mb-2">Data Needs</h3>
              <div className="grid grid-cols-3 gap-2">
                {dataNeedsOptions.map(option => (
                  <Button 
                    key={option}
                    variant={planPrefs.data_needs === option ? "default" : "outline"}
                    size="sm"
                    className="w-full capitalize"
                    onClick={() => setSinglePreference('data_needs', option)}
                  >
                    {option}
                  </Button>
                ))}
              </div>
              <div className="text-xs text-gray-500 mt-1 grid grid-cols-3">
                <span>2-5GB</span>
                <span className="text-center">10-20GB</span>
                <span className="text-right">Unlimited</span>
              </div>
            </div>

            {/* Price Sensitivity */}
            <div>
              <h3 className="text-sm font-medium mb-2">Price Sensitivity</h3>
              <div className="grid grid-cols-3 gap-2">
                {priceSensitivityOptions.map(option => (
                  <Button 
                    key={option}
                    variant={planPrefs.price_sensitivity === option ? "default" : "outline"}
                    size="sm"
                    className="w-full capitalize"
                    onClick={() => setSinglePreference('price_sensitivity', option)}
                  >
                    {option}
                  </Button>
                ))}
              </div>
              <div className="text-xs text-gray-500 mt-1 grid grid-cols-3">
                <span>Budget</span>
                <span className="text-center">Mid-range</span>
                <span className="text-right">Premium</span>
              </div>
            </div>

            {/* Contract Length */}
            <div>
              <h3 className="text-sm font-medium mb-2">Contract Length</h3>
              <div className="grid grid-cols-3 gap-2">
                {contractLengthOptions.map(option => (
                  <Button 
                    key={option}
                    variant={planPrefs.contract_length === option ? "default" : "outline"}
                    size="sm"
                    className="w-full"
                    onClick={() => setSinglePreference('contract_length', option)}
                  >
                    {option === 'monthly' ? 'Monthly' : option === '1-year' ? '1 Year' : '2 Year'}
                  </Button>
                ))}
              </div>
            </div>

            {/* Toggle Switches */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="international">International Usage</Label>
                  <p className="text-xs text-gray-500">Roaming and international calls</p>
                </div>
                <Switch 
                  id="international"
                  checked={planPrefs.international}
                  onCheckedChange={(checked) => setSinglePreference('international', checked)}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="family">Family Plan</Label>
                  <p className="text-xs text-gray-500">Multiple lines on one account</p>
                </div>
                <Switch 
                  id="family"
                  checked={planPrefs.family_plan}
                  onCheckedChange={(checked) => setSinglePreference('family_plan', checked)}
                />
              </div>
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter className="pt-4">
          <Button variant="outline" onClick={() => setIsOpen(false)} className="mr-2">
            Cancel
          </Button>
          <Button onClick={handleSave}>
            Save Preferences
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default UserPreferenceManager;
import React, { useState, useEffect } from 'react';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { ShoppingCart, Plus, Minus, X, AlertCircle, CheckCircle, Package, Zap, Euro } from 'lucide-react';

const CartPreview = ({ sessionId, isOpen, onClose, onToggle, apiBaseUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001' }) => {
  const [cart, setCart] = useState([]);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);

  useEffect(() => {
    if (sessionId && isOpen) {
      fetchCart();
    }
  }, [sessionId, isOpen]);

  const fetchCart = async () => {
    if (!sessionId) return;
    
    try {
      setLoading(true);
      const response = await fetch(`${apiBaseUrl}/api/cart/${sessionId}`);
      const data = await response.json();
      setCart(data);
    } catch (error) {
      console.error('Failed to fetch cart:', error);
      showNotification('Failed to load cart', 'error');
    } finally {
      setLoading(false);
    }
  };

  const updateQuantity = async (itemId, newQuantity) => {
    try {
      const response = await fetch(`${apiBaseUrl}/api/cart/update`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          item_id: itemId,
          quantity: newQuantity
        })
      });

      const result = await response.json();
      if (result.success) {
        setCart(result.cart_summary);
        showNotification(result.message, 'success');
      }
    } catch (error) {
      console.error('Failed to update cart:', error);
      showNotification('Failed to update cart', 'error');
    }
  };

  const clearCart = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/api/cart/${sessionId}/clear`, {
        method: 'DELETE'
      });

      const result = await response.json();
      if (result.success) {
        setCart(result.cart_summary);
        showNotification('Cart cleared', 'success');
      }
    } catch (error) {
      console.error('Failed to clear cart:', error);
      showNotification('Failed to clear cart', 'error');
    }
  };

  const showNotification = (message, type) => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  };

  if (!isOpen) {
    return (
      <div className="fixed bottom-6 right-6 z-50">
        <Button
          onClick={onToggle}
          className="rounded-full w-14 h-14 bg-blue-600 hover:bg-blue-700 shadow-lg relative"
        >
          <ShoppingCart className="w-6 h-6" />
          {cart.total_items > 0 && (
            <Badge className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs">
              {cart.total_items}
            </Badge>
          )}
        </Button>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-end p-6">
      <div className="fixed inset-0 bg-black bg-opacity-20" onClick={onClose}></div>
      
      <Card className="relative w-96 max-h-[80vh] bg-white shadow-2xl animate-slide-up">
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <ShoppingCart className="w-5 h-5" />
            <h3 className="font-semibold">Shopping Cart</h3>
            {cart.total_items > 0 && (
              <Badge variant="secondary">{cart.total_items} items</Badge>
            )}
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        <CardContent className="p-0 overflow-y-auto max-h-96">
          {loading ? (
            <div className="flex items-center justify-center p-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : cart.cart && cart.cart.length > 0 ? (
            <div className="divide-y">
              {cart.cart.map((item) => (
                <div key={`${item.id}-${item.type}`} className="p-4">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        {item.type === 'bundle' && <Package className="w-4 h-4 text-blue-600" />}
                        {item.type === 'device' && <Zap className="w-4 h-4 text-purple-600" />}
                        {item.type === 'plan' && <Zap className="w-4 h-4 text-green-600" />}
                        <h4 className="font-medium text-sm">{item.name}</h4>
                      </div>
                      <p className="text-xs text-gray-500 capitalize">{item.type}</p>
                      
                      {/* Bundle Components */}
                      {item.bundle_components && item.bundle_components.length > 0 && (
                        <div className="mt-2 space-y-1">
                          <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700">
                            <Package className="w-3 h-3 mr-1" />
                            Bundle Deal
                          </Badge>
                          <div className="pl-4 border-l-2 border-blue-100 space-y-1">
                            {item.bundle_components.map((component, idx) => (
                              <div key={idx} className="flex items-center justify-between text-xs">
                                <span className="text-gray-600">• {component.name}</span>
                                <span className="text-gray-500">€{component.price}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-sm">€{item.price.toFixed(2)}</p>
                      {item.original_price && item.original_price > item.price && (
                        <div>
                          <p className="text-xs text-gray-400 line-through">€{item.original_price.toFixed(2)}</p>
                          <p className="text-xs text-green-600 font-medium">
                            Save €{(item.original_price - item.price).toFixed(2)}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-8 h-8 p-0"
                        onClick={() => updateQuantity(item.id, item.quantity - 1)}
                      >
                        <Minus className="w-3 h-3" />
                      </Button>
                      <span className="w-8 text-center text-sm">{item.quantity}</span>
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-8 h-8 p-0"
                        onClick={() => updateQuantity(item.id, item.quantity + 1)}
                      >
                        <Plus className="w-3 h-3" />
                      </Button>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red-600 hover:text-red-700"
                      onClick={() => updateQuantity(item.id, 0)}
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center p-8 text-gray-500">
              <ShoppingCart className="w-12 h-12 mb-4 opacity-50" />
              <p className="text-center">Your cart is empty</p>
              <p className="text-sm text-center mt-1">Add some items to get started!</p>
            </div>
          )}
        </CardContent>

        {cart.cart && cart.cart.length > 0 && (
          <div className="border-t p-4 space-y-4">
            {/* Price Breakdown */}
            {(() => {
              const originalTotal = cart.cart.reduce((sum, item) => 
                sum + (item.original_price || item.price) * item.quantity, 0);
              const totalSavings = originalTotal - cart.total_price;
              const hasDiscount = totalSavings > 0;
              
              return (
                <div className="space-y-2">
                  {hasDiscount && (
                    <>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-gray-600">Subtotal:</span>
                        <span className="line-through text-gray-400">€{originalTotal.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-green-600 flex items-center gap-1">
                          <Euro className="w-3 h-3" />
                          Bundle Savings:
                        </span>
                        <span className="text-green-600 font-medium">-€{totalSavings.toFixed(2)}</span>
                      </div>
                      <hr className="border-gray-200" />
                    </>
                  )}
                  <div className="flex justify-between items-center">
                    <span className="font-semibold">Total:</span>
                    <span className="font-semibold text-lg text-blue-600">€{cart.total_price?.toFixed(2)}</span>
                  </div>
                  {hasDiscount && (
                    <p className="text-xs text-green-600 text-center">
                      🎉 You're saving €{totalSavings.toFixed(2)} with bundle deals!
                    </p>
                  )}
                </div>
              );
            })()}
            
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={clearCart}
              >
                Clear Cart
              </Button>
              <Button className="flex-1 bg-blue-600 hover:bg-blue-700">
                Checkout
              </Button>
            </div>
          </div>
        )}

        {/* Notification */}
        {notification && (
          <div className="fixed top-4 right-4 z-60">
            <div className={`flex items-center gap-2 px-4 py-2 rounded-lg shadow-lg ${
              notification.type === 'success' 
                ? 'bg-green-600 text-white' 
                : 'bg-red-600 text-white'
            }`}>
              {notification.type === 'success' ? 
                <CheckCircle className="w-4 h-4" /> : 
                <AlertCircle className="w-4 h-4" />
              }
              <span className="text-sm">{notification.message}</span>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};

export default CartPreview;
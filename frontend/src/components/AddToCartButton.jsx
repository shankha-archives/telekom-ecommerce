import React, { useState } from 'react';
import { Button } from './ui/button';
import { ShoppingCart, Plus, Check, AlertCircle } from 'lucide-react';

const AddToCartButton = ({ 
  item, 
  itemType, 
  sessionId, 
  onCartUpdate, 
  size = "default",
  variant = "default",
  className = "",
  showIcon = true,
  children,
  apiBaseUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001'
}) => {
  const [isAdding, setIsAdding] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [error, setError] = useState(null);

  const addToCart = async () => {
    if (!sessionId || !item?.id) {
      setError('Session or item not available');
      return;
    }

    try {
      setIsAdding(true);
      setError(null);

      const response = await fetch(`${apiBaseUrl}/api/cart/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          item_id: item.id,
          item_type: itemType,
          quantity: 1
        })
      });

      const result = await response.json();
      
      if (result.success) {
        setShowSuccess(true);
        
        // Trigger cart update in parent component
        if (onCartUpdate) {
          onCartUpdate(result.cart_summary);
        }

        // Show success animation
        setTimeout(() => setShowSuccess(false), 2000);

        // Voice confirmation if supported
        if ('speechSynthesis' in window && result.voice_confirmation) {
          const utterance = new SpeechSynthesisUtterance(result.voice_confirmation);
          utterance.rate = 0.8;
          utterance.volume = 0.7;
          speechSynthesis.speak(utterance);
        }
      } else {
        throw new Error(result.message || 'Failed to add to cart');
      }
    } catch (error) {
      console.error('Add to cart error:', error);
      setError(error.message || 'Failed to add to cart');
      setTimeout(() => setError(null), 3000);
    } finally {
      setIsAdding(false);
    }
  };

  const handleClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    addToCart();
  };

  return (
    <div className="relative">
      <Button
        onClick={handleClick}
        disabled={isAdding || showSuccess}
        size={size}
        variant={showSuccess ? "default" : variant}
        className={`
          transition-all duration-200 
          ${showSuccess ? 'bg-green-600 hover:bg-green-600' : ''}
          ${error ? 'bg-red-600 hover:bg-red-600' : ''}
          ${className}
        `}
      >
        {isAdding ? (
          <>
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
            Adding...
          </>
        ) : showSuccess ? (
          <>
            {showIcon && <Check className="w-4 h-4 mr-2" />}
            Added!
          </>
        ) : error ? (
          <>
            {showIcon && <AlertCircle className="w-4 h-4 mr-2" />}
            Error
          </>
        ) : (
          <>
            {showIcon && <ShoppingCart className="w-4 h-4 mr-2" />}
            {children || 'Add to Cart'}
          </>
        )}
      </Button>

      {/* Success Animation */}
      {showSuccess && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="animate-ping absolute inline-flex h-full w-full rounded-md bg-green-400 opacity-75"></div>
        </div>
      )}

      {/* Cart Icon Animation */}
      {showSuccess && onCartUpdate && (
        <div className="absolute top-0 right-0 transform translate-x-2 -translate-y-2">
          <div className="animate-bounce">
            <div className="bg-green-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs">
              <Plus className="w-3 h-3" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AddToCartButton;
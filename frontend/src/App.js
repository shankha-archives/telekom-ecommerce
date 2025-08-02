import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Mic, MicOff, Search, ShoppingCart, Star, Phone, Smartphone, Wifi, CheckCircle, X, MessageCircle, RotateCcw } from 'lucide-react';
import ModernChatInterface from './components/ModernChatInterface';
import BundleRecommendations from './components/BundleRecommendations';
import sessionSync from './utils/SessionSync';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [devices, setDevices] = useState([]);
  const [plans, setPlans] = useState([]);
  const [featuredDevices, setFeaturedDevices] = useState([]);
  const [popularPlans, setPopularPlans] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [isListening, setIsListening] = useState(false);
  const [voiceResponse, setVoiceResponse] = useState('');
  const [cart, setCart] = useState([]);
  const [currentView, setCurrentView] = useState('home');
  const [language, setLanguage] = useState('en');
  const [sessionId, setSessionId] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [isChatExpanded, setIsChatExpanded] = useState(false);
  const [isChatMinimized, setIsChatMinimized] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [lastSearchResults, setLastSearchResults] = useState(null);
  const [isInConversationMode, setIsInConversationMode] = useState(false);
  const recognitionRef = useRef(null);

  useEffect(() => {
    async function initializeApp() {
      // Initialize session sync
      const sid = await sessionSync.initialize();
      setSessionId(sid);
      console.log(`Session initialized with ID: ${sid}`);
      
      // Fetch initial cart state
      await fetchCartStateWithId(sid);
      
      // Fetch data and initialize speech
      fetchAllData();
      initializeSpeechRecognition();
    }
    
    initializeApp();

    // Add global cleanup for speech recognition
    const handleBeforeUnload = () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
          recognitionRef.current.abort();
        } catch (error) {
          console.log('Error stopping speech recognition on unload:', error);
        }
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    
    // Add click outside listener to close chat
    const handleClickOutside = (event) => {
      const chatContainer = document.querySelector('.chat-container');
      const searchInput = document.querySelector('input[placeholder*="Ask me anything"]');
      
      if (isChatExpanded && chatContainer && !chatContainer.contains(event.target) && !searchInput.contains(event.target)) {
        minimizeChat();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('beforeunload', handleBeforeUnload);
      sessionSync.cleanup();
      // Cleanup speech recognition
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
          recognitionRef.current.abort();
        } catch (error) {
          console.log('Error cleaning up speech recognition:', error);
        }
      }
    };
  }, [isChatExpanded]);

  const expandChatWithGreeting = () => {
    if (!isChatExpanded) {
      setIsChatExpanded(true);
      setIsChatMinimized(false);
      // Only add greeting if there's no chat history
      if (chatHistory.length === 0) {
        const greeting = language === 'hi' 
          ? "नमस्ते! मैं आपका Telekom असिस्ट्रेंट हूं। मैं आपको बेहतरीन डिवाइस और प्लान खोजने में मदद कर सकता हूं। आपको क्या चाहिए?"
          : "Hello! I'm your Telekom assistant. I can help you find the perfect devices and plans. What can I help you with today?";
        
        setChatHistory([{
          type: 'assistant',
          message: greeting,
          timestamp: new Date().toISOString()
        }]);
      }
    }
  };

  const fetchAllData = async () => {
    try {
      const [featuredRes, popularRes, allDevicesRes, allPlansRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/featured-devices`),
        fetch(`${BACKEND_URL}/api/popular-plans`),
        fetch(`${BACKEND_URL}/api/devices`),
        fetch(`${BACKEND_URL}/api/plans`)
      ]);
      
      const featuredDevices = await featuredRes.json();
      const popularPlans = await popularRes.json();
      const allDevices = await allDevicesRes.json();
      const allPlans = await allPlansRes.json();
      
      setFeaturedDevices(featuredDevices);
      setPopularPlans(popularPlans);
      setDevices(allDevices);
      setPlans(allPlans);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  const initializeSpeechRecognition = () => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = language === 'hi' ? 'hi-IN' : 'en-US';

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        handleVoiceSearch(transcript);
      };

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }
  };

  const toggleVoiceSearch = () => {
    if (!isChatExpanded) {
      expandChatWithGreeting();
    }

    if (isListening) {
      // Stop current recognition
      try {
        recognitionRef.current?.stop();
      } catch (error) {
        console.log('Error stopping recognition:', error);
      }
      setIsListening(false);
      setIsInConversationMode(false);
    } else {
      if (recognitionRef.current) {
        try {
          // Always stop first to ensure clean state
          recognitionRef.current.stop();
        } catch (error) {
          // Ignore errors when stopping (might not be running)
        }
        
        try {
          // Small delay to ensure stop is processed
          setTimeout(() => {
            if (recognitionRef.current && !isListening) {
              recognitionRef.current.lang = language === 'hi' ? 'hi-IN' : 'en-US';
              recognitionRef.current.start();
              setIsListening(true);
              setIsInConversationMode(true);
            }
          }, 100);
        } catch (error) {
          console.error('Error starting recognition:', error);
          setIsListening(false);
          setIsInConversationMode(false);
        }
      } else {
        alert('Speech recognition not supported in your browser');
      }
    }
  };

  const startListeningAfterResponse = () => {
    if (isInConversationMode && !isChatMinimized && !isListening) {
      setTimeout(() => {
        if (recognitionRef.current && isInConversationMode && !isListening) {
          try {
            // Ensure clean state before starting
            recognitionRef.current.stop();
          } catch (error) {
            // Ignore stop errors
          }
          
          setTimeout(() => {
            if (recognitionRef.current && isInConversationMode && !isListening) {
              try {
                recognitionRef.current.start();
                setIsListening(true);
              } catch (error) {
                console.error('Error restarting recognition:', error);
                setIsListening(false);
              }
            }
          }, 100); // Small delay after stop
        }
      }, 1000); // 1 second delay
    }
  };

  const minimizeChat = () => {
    setIsChatExpanded(false);
    setIsChatMinimized(false); // Don't show minimized state, just close
    setIsListening(false);
    setIsInConversationMode(false);
    recognitionRef.current?.stop();
  };

  const maximizeChat = () => {
    setIsChatExpanded(true);
    setIsChatMinimized(false);
  };

  const handleVoiceSearch = async (transcript) => {
    // Expand chat if not already expanded
    if (!isChatExpanded) {
      expandChatWithGreeting();
    }

    // Add user message to chat
    const userMessage = {
      type: 'user',
      message: transcript,
      timestamp: new Date().toISOString()
    };
    setChatHistory(prev => [...prev, userMessage]);
    setIsTyping(true);

    try {
      const response = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: transcript,
          session_id: sessionId,
          language: language,
          chat_history: chatHistory.slice(-10) // Send last 10 messages for better context
        })
      });

      const result = await response.json();
      
      // Add assistant response to chat
      const assistantMessage = {
        type: 'assistant',
        message: result.response,
        timestamp: new Date().toISOString(),
        follow_up_questions: result.follow_up_questions || []
      };
      
      setChatHistory(prev => [...prev, assistantMessage]);
      setIsTyping(false);
      
      // Handle recommendations
      if (result.recommendations) {
        const searchResultsData = {
          devices: result.recommendations.devices || [],
          plans: result.recommendations.plans || [],
          recommendation: result.response
        };
        setLastSearchResults(searchResultsData);
        
        // Add search results to chat
        if (searchResultsData.devices.length > 0 || searchResultsData.plans.length > 0) {
          const resultsMessage = {
            type: 'results',
            devices: searchResultsData.devices,
            plans: searchResultsData.plans,
            timestamp: new Date().toISOString()
          };
          setChatHistory(prev => [...prev, resultsMessage]);
        }
      }
      
      // Handle cart actions - only if not already processed by backend
      if (result.cart_items && result.cart_items.length > 0 && !result.cart_action) {
        result.cart_items.forEach(item => {
          addToCart(item, item.type);
        });
      } else if (result.cart_action && result.cart_summary) {
        // Cart was already processed by backend, just refresh our cart state
        await fetchCartState();
      }
      
      // Handle cart navigation
      if (result.navigate_to_cart) {
        // Wait a moment for the cart state to update, then navigate
        setTimeout(() => {
          setCurrentView('cart');
          // Close chat to show cart clearly
          setIsChatExpanded(false);
        }, 1000);
      }
      
      // Speak the response with smart content
      if ('speechSynthesis' in window && result.response) {
        const utterance = new SpeechSynthesisUtterance(result.speech_text || result.response);
        utterance.lang = language === 'hi' ? 'hi-IN' : 'en-US';
        utterance.rate = 0.9;
        
        utterance.onend = () => {
          startListeningAfterResponse();
        };
        
        speechSynthesis.speak(utterance);
      }
    } catch (error) {
      console.error('Voice search error:', error);
      const errorMessage = {
        type: 'assistant',
        message: 'Sorry, I encountered an error processing your request.',
        timestamp: new Date().toISOString()
      };
      setChatHistory(prev => [...prev, errorMessage]);
      setIsTyping(false);
    }
  };

  const handleChatInput = async () => {
    if (!chatInput.trim()) return;
    
    const userInput = chatInput;
    setChatInput('');
    await handleVoiceSearch(userInput);
  };

  const handleSearchFocus = () => {
    expandChatWithGreeting();
  };

  const startOver = () => {
    setChatHistory([{
      type: 'assistant',
      message: language === 'hi' 
        ? "नमस्ते! मैं आपका Telekom असिस्ट्रेंट हूं। आपको क्या चाहिए?"
        : "Hello! I'm your Telekom assistant. What can I help you with today?",
      timestamp: new Date().toISOString()
    }]);
    setLastSearchResults(null);
    setSearchResults(null);
    setChatInput('');
  };

  const closeChatExpansion = () => {
    setIsChatExpanded(false);
    setIsChatMinimized(false);
    // Keep chat history - this was the bug!
    setLastSearchResults(null);
    setIsListening(false);
    setIsInConversationMode(false);
    recognitionRef.current?.stop();
  };

  const handleTextSearch = async () => {
    if (!searchQuery.trim()) return;

    try {
      const response = await fetch(`${BACKEND_URL}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: searchQuery,
          session_id: sessionId
        })
      });

      const results = await response.json();
      
      // If using enhanced API
      if (results.recommendations) {
        setSearchResults({
          devices: results.recommendations.devices || [],
          plans: results.recommendations.plans || [],
          recommendation: results.response
        });
      } else {
        // Legacy format
        setSearchResults(results);
      }
      
      setCurrentView('search');
    } catch (error) {
      console.error('Search error:', error);
    }
  };

  const fetchCartStateWithId = async (sid) => {
    if (!sid) return;
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/cart/${sid}`);
      const cartData = await response.json();
      
      if (cartData.cart) {
        // Convert backend cart format to frontend format
        const frontendCart = cartData.cart.map(item => ({
          id: item.id,
          name: item.name,
          price: item.price,
          type: item.type,
          image: item.image || null
        }));
        setCart(frontendCart);
      }
    } catch (error) {
      console.error('Failed to fetch cart state:', error);
    }
  };

  const fetchCartState = async () => {
    return fetchCartStateWithId(sessionId);
  };

  const addToCart = async (item, type) => {
    if (!sessionId || !item?.id) {
      console.error('Session or item not available');
      return;
    }

    try {
      const response = await fetch(`${BACKEND_URL}/api/cart/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          item_id: item.id,
          item_type: type,
          quantity: 1
        })
      });

      const result = await response.json();
      
      if (result.success) {
        // Update cart state with backend response
        await fetchCartState();
        
        // Track conversion event
        sessionSync.trackConversion({
          item_id: item.id,
          item_type: type,
          item_data: item,
          conversion_step: 'add_to_cart'
        });
        
        // Add confirmation message to chat if chat is expanded
        if (isChatExpanded) {
          const confirmMessage = {
            type: 'assistant',
            message: `✅ Added ${item.name} to your cart!`,
            timestamp: new Date().toISOString()
          };
          setChatHistory(prev => [...prev, confirmMessage]);
        }

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
      // Show error message to user
      if (isChatExpanded) {
        const errorMessage = {
          type: 'assistant',
          message: `Sorry, I couldn't add ${item.name} to your cart. Please try again.`,
          timestamp: new Date().toISOString()
        };
        setChatHistory(prev => [...prev, errorMessage]);
      }
    }
  };

  const handleCartUpdate = async (cartSummary) => {
    // Refresh cart state when notified of updates
    await fetchCartState();
    console.log('Cart updated:', cartSummary);
  };

  const DeviceCard = ({ device, showInChat = false }) => (
    <Card className={`group hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 bg-white/90 backdrop-blur-sm border-0 shadow-lg ${showInChat ? 'mb-4' : ''}`}>
      <CardHeader className="p-0">
        <div className="relative overflow-hidden rounded-t-lg">
          <img 
            src={device.image} 
            alt={device.name}
            className="w-full h-48 object-cover group-hover:scale-105 transition-transform duration-300"
            onError={(e) => {
              e.target.src = 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=60';
            }}
          />
          <div className="absolute top-3 right-3">
            <Badge variant="secondary" className="bg-magenta-500 text-white">
              {device.original_price ? `Save €${(device.original_price - device.price).toFixed(0)}` : 'New'}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-bold text-lg text-gray-900">{device.name}</h3>
          <div className="flex items-center gap-1">
            <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
            <span className="text-sm text-gray-600">{device.rating}</span>
          </div>
        </div>
        <p className="text-gray-600 text-sm mb-3 line-clamp-2">{device.description}</p>
        <div className="flex flex-wrap gap-1 mb-3">
          {device.features?.slice(0, 2).map((feature, idx) => (
            <Badge key={idx} variant="outline" className="text-xs">{feature}</Badge>
          ))}
        </div>
        <div className="flex items-center justify-between">
          <div>
            {device.original_price && (
              <span className="text-sm text-gray-500 line-through">€{device.original_price}</span>
            )}
            <span className="text-xl font-bold text-magenta-600 ml-2">€{device.price}</span>
          </div>
          <Button 
            onClick={() => addToCart(device, 'device')}
            className="bg-magenta-600 hover:bg-magenta-700 text-white px-4 py-2 rounded-lg transition-colors"
            size={showInChat ? "sm" : "default"}
          >
            Add to Cart
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  const PlanCard = ({ plan, showInChat = false }) => (
    <Card className={`relative transition-all duration-300 hover:shadow-xl ${plan.popular ? 'ring-2 ring-magenta-500 transform scale-105' : ''} bg-white/90 backdrop-blur-sm border-0 shadow-lg ${showInChat ? 'mb-4' : ''}`}>
      {plan.popular && (
        <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
          <Badge className="bg-magenta-500 text-white px-3 py-1">Most Popular</Badge>
        </div>
      )}
      <CardHeader className="text-center pb-4">
        <CardTitle className="text-2xl font-bold text-gray-900">{plan.name}</CardTitle>
        <div className="mt-2">
          <span className="text-3xl font-bold text-magenta-600">€{plan.price}</span>
          <span className="text-gray-600">/{plan.duration}</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <Wifi className="w-5 h-5 text-magenta-500" />
            <span><strong>{plan.data}</strong> Data</span>
          </div>
          <div className="flex items-center gap-3">
            <Phone className="w-5 h-5 text-magenta-500" />
            <span><strong>{plan.minutes}</strong> Minutes</span>
          </div>
          <div className="flex items-center gap-3">
            <Smartphone className="w-5 h-5 text-magenta-500" />
            <span><strong>{plan.sms}</strong> SMS</span>
          </div>
        </div>
        <div className="border-t pt-4">
          <h4 className="font-semibold mb-2">Included:</h4>
          <ul className="space-y-1">
            {plan.features?.map((feature, idx) => (
              <li key={idx} className="flex items-center gap-2 text-sm">
                <CheckCircle className="w-4 h-4 text-green-500" />
                {feature}
              </li>
            ))}
          </ul>
        </div>
        <Button 
          onClick={() => addToCart(plan, 'plan')}
          className={`w-full mt-4 transition-colors ${plan.popular ? 'bg-magenta-600 hover:bg-magenta-700' : 'bg-gray-800 hover:bg-gray-900'} text-white`}
          size={showInChat ? "sm" : "default"}
        >
          Choose Plan
        </Button>
      </CardContent>
    </Card>
  );

  const renderHome = () => (
    <div>
      {/* Hero Section */}
      <section className="relative h-96 bg-gradient-to-r from-magenta-600 to-purple-700 text-white overflow-hidden">
        <div className="absolute inset-0 bg-black/20"></div>
        <div className="relative max-w-6xl mx-auto px-4 h-full flex items-center">
          <div className="grid md:grid-cols-2 gap-8 items-center w-full">
            <div>
              <h1 className="text-4xl md:text-5xl font-bold mb-4">
                Smart Devices, Smarter Plans
              </h1>
              <p className="text-xl mb-6 opacity-90">
                Discover the latest smartphones and find the perfect plan with our AI-powered assistant
              </p>
              <div className="flex gap-4">
                <Button size="lg" className="bg-white text-magenta-600 hover:bg-gray-100">
                  Explore Devices
                </Button>
                <Button size="lg" variant="outline" className="border-white text-white hover:bg-white hover:text-magenta-600">
                  View Plans
                </Button>
              </div>
            </div>
            <div className="hidden md:block">
              <img 
                src="https://images.unsplash.com/photo-1511707171634-5f897ff02aa9" 
                alt="Latest Smartphone"
                className="rounded-lg shadow-2xl max-w-md"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Featured Devices */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-6xl mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Featured Devices</h2>
            <p className="text-gray-600 max-w-2xl mx-auto">
              Discover our handpicked selection of the latest smartphones with cutting-edge technology
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {featuredDevices.map((device) => (
              <DeviceCard key={device.id} device={device} />
            ))}
          </div>
        </div>
      </section>

      {/* Popular Plans */}
      <section className="py-16 bg-white">
        <div className="max-w-6xl mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Popular Plans</h2>
            <p className="text-gray-600 max-w-2xl mx-auto">
              Choose from our most popular mobile plans designed to fit your lifestyle
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-4xl mx-auto">
            {popularPlans.map((plan) => (
              <PlanCard key={plan.id} plan={plan} />
            ))}
          </div>
        </div>
      </section>

      {/* Bundle Recommendations */}
      {sessionId && (
        <section className="py-16 bg-gradient-to-br from-blue-50 to-purple-50">
          <div className="max-w-6xl mx-auto px-4">
            <BundleRecommendations
              sessionId={sessionId}
              apiBaseUrl={BACKEND_URL}
              onCartUpdate={handleCartUpdate}
            />
          </div>
        </section>
      )}
    </div>
  );

  const renderSearch = () => (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h2 className="text-2xl font-bold mb-6">Search Results</h2>
      {searchResults && (
        <div>
          {searchResults.recommendation && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
              <p className="text-blue-800">{searchResults.recommendation}</p>
            </div>
          )}
          
          {searchResults.devices && searchResults.devices.length > 0 && (
            <div className="mb-8">
              <h3 className="text-xl font-semibold mb-4">Recommended Devices</h3>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {searchResults.devices.map((device) => (
                  <DeviceCard key={device.id} device={device} />
                ))}
              </div>
            </div>
          )}
          
          {searchResults.plans && searchResults.plans.length > 0 && (
            <div>
              <h3 className="text-xl font-semibold mb-4">Recommended Plans</h3>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {searchResults.plans.map((plan) => (
                  <PlanCard key={plan.id} plan={plan} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );

  const renderCart = () => (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Your Cart</h1>
        <Button 
          onClick={() => setCurrentView('home')}
          variant="outline"
          className="flex items-center gap-2"
        >
          ← Back to Home
        </Button>
      </div>

      {cart.length === 0 ? (
        <div className="text-center py-16">
          <ShoppingCart className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-600 mb-2">Your cart is empty</h2>
          <p className="text-gray-500 mb-6">Add some devices or plans to get started</p>
          <Button 
            onClick={() => setCurrentView('home')}
            className="bg-magenta-600 hover:bg-magenta-700"
          >
            Continue Shopping
          </Button>
        </div>
      ) : (
        <div className="space-y-6">
          {cart.map((item, index) => (
            <Card key={index} className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {item.image && (
                    <img src={item.image} alt={item.name} className="w-16 h-16 object-cover rounded-lg" />
                  )}
                  <div>
                    <h3 className="font-semibold text-lg">{item.name}</h3>
                    <p className="text-gray-600 capitalize">{item.type}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xl font-bold text-magenta-600">€{item.price}</p>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => setCart(cart.filter((_, i) => i !== index))}
                    className="text-red-500 hover:text-red-700"
                  >
                    Remove
                  </Button>
                </div>
              </div>
            </Card>
          ))}
          
          <Card className="p-6 bg-gray-50">
            <div className="flex justify-between items-center mb-4">
              <span className="text-xl font-semibold">Total:</span>
              <span className="text-2xl font-bold text-magenta-600">
                €{cart.reduce((total, item) => total + item.price, 0).toFixed(2)}
              </span>
            </div>
            <Button className="w-full bg-magenta-600 hover:bg-magenta-700 text-lg py-3">
              Proceed to Checkout
            </Button>
          </Card>
        </div>
      )}
    </div>
  );

  const renderDevices = () => (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">All Devices</h1>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Explore our complete collection of premium smartphones with cutting-edge technology
        </p>
      </div>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
        {devices.map((device) => (
          <DeviceCard key={device.id} device={device} />
        ))}
      </div>
    </div>
  );

  const renderPlans = () => (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">All Plans</h1>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Choose from our comprehensive range of mobile plans designed for every lifestyle
        </p>
      </div>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-5xl mx-auto">
        {plans.map((plan) => (
          <PlanCard key={plan.id} plan={plan} />
        ))}
      </div>
    </div>
  );

  const ChatMessage = ({ message }) => {
    if (message.type === 'results') {
      return (
        <div className="mb-4">
          {message.devices && message.devices.length > 0 && (
            <div className="mb-4">
              <h4 className="font-semibold mb-2 text-gray-700">📱 Recommended Devices:</h4>
              <div className="grid gap-3">
                {message.devices.map((device) => (
                  <DeviceCard key={device.id} device={device} showInChat={true} />
                ))}
              </div>
            </div>
          )}
          {message.plans && message.plans.length > 0 && (
            <div>
              <h4 className="font-semibold mb-2 text-gray-700">📋 Recommended Plans:</h4>
              <div className="grid gap-3">
                {message.plans.map((plan) => (
                  <PlanCard key={plan.id} plan={plan} showInChat={true} />
                ))}
              </div>
            </div>
          )}
        </div>
      );
    }

    return (
      <div className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} mb-3`}>
        <div className={`max-w-xs lg:max-w-md px-4 py-3 rounded-2xl shadow-sm ${
          message.type === 'user' 
            ? 'bg-magenta-600 text-white rounded-br-md' 
            : 'bg-white border text-gray-800 rounded-bl-md'
        }`}>
          <p className="text-sm leading-relaxed">{message.message}</p>
          <span className="text-xs opacity-70 mt-1 block">
            {new Date(message.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
          </span>
        </div>
      </div>
    );
  };

  const ExpandedChatInterface = () => {
    return (
      <div className="absolute top-full left-0 right-0 z-50 overflow-hidden">
        <div className="w-full h-[500px]">
          <ModernChatInterface
            sessionId={sessionId}
            apiBaseUrl={BACKEND_URL}
            onMinimize={minimizeChat}
            onClose={closeChatExpansion}
            onRestart={startOver}
            language={language}
            initialMessages={chatHistory}
          />
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-magenta-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold">T</span>
              </div>
              <span className="text-xl font-bold text-gray-900">Telekom</span>
            </div>
            
            {/* Smart Search Bar */}
            <div className="flex-1 max-w-2xl mx-8 relative chat-container">
              <div className="relative">
                <Input
                  placeholder="Ask me anything about devices and plans..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleTextSearch()}
                  onFocus={handleSearchFocus}
                  className={`pr-20 h-12 border-gray-300 focus:border-magenta-500 focus:ring-magenta-500 rounded-xl transition-all duration-300 ${
                    isChatExpanded ? 'rounded-b-none border-b-0' : ''
                  }`}
                />
                <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex gap-2">
                  <button
                    onClick={toggleVoiceSearch}
                    className={`p-2 rounded-full transition-colors ${
                      isListening 
                        ? 'bg-red-500 text-white animate-pulse' 
                        : 'bg-gray-100 hover:bg-gray-200'
                    }`}
                  >
                    {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={handleTextSearch}
                    className="p-2 bg-magenta-600 text-white rounded-full hover:bg-magenta-700 transition-colors"
                  >
                    <Search className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              {/* Expanded Chat Interface */}
              {isChatExpanded && <ExpandedChatInterface />}
            </div>

            <div className="flex items-center gap-4">
              <select 
                value={language} 
                onChange={(e) => setLanguage(e.target.value)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="en">🇺🇸 English</option>
                <option value="hi">🇮🇳 हिंदी</option>
              </select>
              
              <Button 
                variant="outline" 
                className="relative"
                onClick={() => setCurrentView('cart')}
              >
                <ShoppingCart className="w-4 h-4 mr-2" />
                Cart
                {cart.length > 0 && (
                  <Badge className="absolute -top-2 -right-2 bg-magenta-500 text-white text-xs">
                    {cart.length}
                  </Badge>
                )}
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Voice Response Display */}
      {voiceResponse && (
        <div className="bg-magenta-50 border-b border-magenta-200">
          <div className="max-w-6xl mx-auto px-4 py-3">
            <div className="flex items-center gap-2">
              <Mic className="w-4 h-4 text-magenta-600" />
              <span className="text-magenta-800">{voiceResponse}</span>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="bg-white border-b">
        <div className="max-w-6xl mx-auto px-4">
          <div className="flex gap-8">
            <button
              onClick={() => setCurrentView('home')}
              className={`py-4 px-2 border-b-2 transition-colors ${currentView === 'home' ? 'border-magenta-500 text-magenta-600' : 'border-transparent text-gray-600 hover:text-gray-900'}`}
            >
              Home
            </button>
            <button
              onClick={() => setCurrentView('devices')}
              className={`py-4 px-2 border-b-2 transition-colors ${currentView === 'devices' ? 'border-magenta-500 text-magenta-600' : 'border-transparent text-gray-600 hover:text-gray-900'}`}
            >
              Devices
            </button>
            <button
              onClick={() => setCurrentView('plans')}
              className={`py-4 px-2 border-b-2 transition-colors ${currentView === 'plans' ? 'border-magenta-500 text-magenta-600' : 'border-transparent text-gray-600 hover:text-gray-900'}`}
            >
              Plans
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className={isChatExpanded ? 'pt-0' : ''}>
        {currentView === 'home' && renderHome()}
        {currentView === 'devices' && renderDevices()}
        {currentView === 'plans' && renderPlans()}
        {currentView === 'search' && renderSearch()}
        {currentView === 'cart' && renderCart()}
      </main>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12 mt-16">
        <div className="max-w-6xl mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-magenta-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold">T</span>
                </div>
                <span className="text-xl font-bold">Telekom</span>
              </div>
              <p className="text-gray-400">Smart devices and plans for the connected world.</p>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Products</h3>
              <ul className="space-y-2 text-gray-400">
                <li>Smartphones</li>
                <li>Mobile Plans</li>
                <li>Accessories</li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Support</h3>
              <ul className="space-y-2 text-gray-400">
                <li>Customer Service</li>
                <li>Technical Support</li>
                <li>Store Locator</li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Company</h3>
              <ul className="space-y-2 text-gray-400">
                <li>About Us</li>
                <li>Careers</li>
                <li>Press</li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
            <p>&copy; 2025 Telekom. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
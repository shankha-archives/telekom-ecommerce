import React, { useState, useEffect, useRef } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Mic, MicOff, Send, RotateCcw, X, Minus, MessageCircle } from 'lucide-react';
import EnhancedChatMessage from './EnhancedChatMessage';
import UserPreferenceManager from './UserPreferenceManager';
import ChatContextIndicator from './ChatContextIndicator';

/**
 * ModernChatInterface Component
 * 
 * A modernized chat interface that integrates EnhancedChatMessage,
 * UserPreferenceManager, and ChatContextIndicator components.
 * 
 * This component handles the conversation flow, message display,
 * voice input, and user preferences.
 */
const ModernChatInterface = ({
  sessionId,
  apiBaseUrl = 'http://localhost:8001',
  onMinimize,
  onClose,
  onRestart,
  language = 'en',
  initialMessages = []
}) => {
  const [chatHistory, setChatHistory] = useState(initialMessages);
  const [chatInput, setChatInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [session, setSession] = useState(null);
  const [explanations, setExplanations] = useState({});
  const recognitionRef = useRef(null);
  const chatContainerRef = useRef(null);

  useEffect(() => {
    initializeSpeechRecognition();
    fetchSessionData();

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, [sessionId]);

  useEffect(() => {
    // Scroll to bottom when chat history changes
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatHistory]);

  const initializeSpeechRecognition = () => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = language === 'hi' ? 'hi-IN' : 'en-US';

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        handleVoiceInput(transcript);
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

  const fetchSessionData = async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(`${apiBaseUrl}/api/session/${sessionId}`);
      if (response.ok) {
        const sessionData = await response.json();
        setSession(sessionData);
      }
    } catch (error) {
      console.error('Error fetching session data:', error);
    }
  };

  const toggleVoiceInput = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      if (recognitionRef.current) {
        recognitionRef.current.lang = language === 'hi' ? 'hi-IN' : 'en-US';
        recognitionRef.current.start();
        setIsListening(true);
      } else {
        alert('Speech recognition not supported in your browser');
      }
    }
  };

  const handleVoiceInput = (transcript) => {
    // Add user message to chat
    const userMessage = {
      type: 'user',
      message: transcript,
      timestamp: new Date().toISOString()
    };

    setChatHistory(prev => [...prev, userMessage]);
    setChatInput('');
    sendMessageToBackend(transcript);
  };

  const handleTextInput = () => {
    if (!chatInput.trim()) return;

    const userInput = chatInput;
    setChatInput('');
    
    // Add user message to chat
    const userMessage = {
      type: 'user',
      message: userInput,
      timestamp: new Date().toISOString()
    };
    
    setChatHistory(prev => [...prev, userMessage]);
    sendMessageToBackend(userInput);
  };

  const sendMessageToBackend = async (message) => {
    setIsTyping(true);

    try {
      const response = await fetch(`${apiBaseUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: message,
          session_id: sessionId,
          language: language,
          // Send last 10 messages for better context
          chat_history: chatHistory.slice(-10)
        })
      });

      const result = await response.json();
      
      // Update the session data
      if (result.session) {
        setSession(result.session);
      }

      // Add assistant response to chat
      const assistantMessage = {
        type: 'assistant',
        message: result.response,
        timestamp: new Date().toISOString(),
        follow_up_questions: result.follow_up_questions || []
      };
      
      setChatHistory(prev => [...prev, assistantMessage]);
      
      // Handle different response types
      if (result.recommendations) {
        // Store any explanations
        if (result.explanations) {
          setExplanations(result.explanations);
        }
        
        // Add results message if there are recommendations
        if (result.recommendations.devices?.length > 0 || result.recommendations.plans?.length > 0) {
          const resultsMessage = {
            type: 'results',
            devices: result.recommendations.devices || [],
            plans: result.recommendations.plans || [],
            timestamp: new Date().toISOString()
          };
          setChatHistory(prev => [...prev, resultsMessage]);
        }
      }
      
      // Handle preference summary if provided
      if (result.preference_summary && result.preference_summary.length > 0) {
        const preferencesMessage = {
          type: 'preferences',
          preferences: result.preference_summary,
          timestamp: new Date().toISOString()
        };
        setChatHistory(prev => [...prev, preferencesMessage]);
      }
      
      // Handle comparison view if provided
      if (result.comparison) {
        const comparisonMessage = {
          type: 'comparison',
          items: result.comparison.items,
          comparisonPoints: result.comparison.points,
          timestamp: new Date().toISOString()
        };
        setChatHistory(prev => [...prev, comparisonMessage]);
      }
      
    } catch (error) {
      console.error('Chat API error:', error);
      
      // Add error message
      const errorMessage = {
        type: 'assistant',
        message: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString()
      };
      
      setChatHistory(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleActionClick = (action) => {
    if (action === 'edit_preferences') {
      // This will be handled by the UserPreferenceManager component
    } else {
      // For suggested questions/follow-ups, send them as user input
      setChatInput(action);
      sendMessageToBackend(action);
      
      // Add as user message
      const userMessage = {
        type: 'user',
        message: action,
        timestamp: new Date().toISOString()
      };
      
      setChatHistory(prev => [...prev, userMessage]);
    }
  };

  const handlePreferencesUpdate = (updatedPreferences) => {
    // Update the session with new preferences
    setSession(prev => ({
      ...prev,
      user_preferences: updatedPreferences
    }));
    
    // Add a confirmation message
    const confirmationMessage = {
      type: 'assistant',
      message: 'Your preferences have been updated. I\'ll take these into account for future recommendations.',
      timestamp: new Date().toISOString()
    };
    
    setChatHistory(prev => [...prev, confirmationMessage]);
  };

  return (
    <div className="flex flex-col h-full bg-white border border-gray-200 rounded-lg shadow-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-3 bg-gradient-to-r from-magenta-600 to-magenta-700 text-white">
        <div className="flex items-center gap-2">
          <MessageCircle className="w-5 h-5" />
          <span className="font-semibold">Your Telekom Assistant</span>
          {isListening && (
            <div className="flex items-center gap-1 ml-2">
              <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse"></div>
              <span className="text-xs">Listening...</span>
            </div>
          )}
        </div>
        <div className="flex gap-1">
          <Button
            onClick={onMinimize}
            variant="ghost"
            size="sm"
            className="text-white hover:bg-magenta-800 p-2 h-8 w-8"
            title="Minimize Chat"
          >
            <Minus className="w-4 h-4" />
          </Button>
          <Button
            onClick={onRestart}
            variant="ghost"
            size="sm"
            className="text-white hover:bg-magenta-800 p-2 h-8 w-8"
            title="Start Over"
          >
            <RotateCcw className="w-4 h-4" />
          </Button>
          <Button
            onClick={onClose}
            variant="ghost" 
            size="sm"
            className="text-white hover:bg-magenta-800 p-2 h-8 w-8"
            title="Close Chat"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>
      
      {/* Context Indicator */}
      <ChatContextIndicator session={session} />
      
      {/* Messages Container */}
      <div 
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto p-4 bg-gray-50 space-y-4 chat-scrollbar"
      >
        {chatHistory.map((message, index) => (
          <EnhancedChatMessage 
            key={index} 
            message={message} 
            onActionClick={handleActionClick}
            explanations={message.type === 'results' ? explanations : {}}
          />
        ))}
        
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-white border px-4 py-3 rounded-2xl rounded-bl-md shadow-sm">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-magenta-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-magenta-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                <div className="w-2 h-2 bg-magenta-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Input Area */}
      <div className="border-t p-3 bg-white">
        <div className="flex items-center gap-2">
          {/* Preference Manager Button */}
          <UserPreferenceManager 
            sessionId={sessionId} 
            preferences={session?.user_preferences}
            onUpdate={handlePreferencesUpdate}
            apiBaseUrl={apiBaseUrl}
          />
          
          {/* Chat Input */}
          <div className="flex-1 flex gap-2">
            <Input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleTextInput()}
              placeholder={isListening ? "Listening..." : "Type your message..."}
              className="flex-1 rounded-xl border-gray-300 focus:border-magenta-500 focus:ring-magenta-500"
              disabled={isListening}
            />
            <Button
              onClick={handleTextInput}
              size="sm"
              className="bg-magenta-600 hover:bg-magenta-700 px-4 rounded-xl"
              disabled={!chatInput.trim() || isListening}
            >
              <Send className="w-4 h-4" />
            </Button>
            <Button
              onClick={toggleVoiceInput}
              size="sm"
              className={`px-4 rounded-xl transition-colors ${
                isListening 
                  ? 'bg-red-500 hover:bg-red-600 text-white' 
                  : 'bg-gray-500 hover:bg-gray-600 text-white'
              }`}
            >
              {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModernChatInterface;
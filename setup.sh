#!/bin/bash

# Telekom Ecommerce - Quick Setup Script

echo "🚀 Setting up Telekom Ecommerce with AI Voice Assistant..."

# Check if we're in the right directory
if [ ! -f "README.md" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Backend setup
echo "📦 Setting up Backend..."
cd backend-copy

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Python dependencies. Please check your Python installation."
    exit 1
fi

cd ..

# Frontend setup
echo "📦 Setting up Frontend..."
cd frontend

# Install Node dependencies
echo "Installing Node.js dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Node.js dependencies. Please check your Node.js installation."
    exit 1
fi

cd ..

echo "✅ Setup complete!"
echo ""
echo "🔑 Next Steps:"
echo "1. Add your OpenAI API key to backend/.env:"
echo "   OPENAI_API_KEY=\"your-api-key-here\""
echo ""
echo "2. Start the application:"
echo "   Terminal 1: cd backend && python server.py"
echo "   Terminal 2: cd frontend && npm start"
echo ""
echo "🌐 The app will be available at:"
echo "   Frontend: http://localhost:3000"
echo "   Backend: http://localhost:8001"
echo ""
echo "🎤 Voice Assistant Features:"
echo "   - Click search bar to open chat"
echo "   - Click microphone for voice mode"
echo "   - Supports Hindi and English"
echo "   - Intelligent speech error correction"
echo ""
echo "Happy coding! 🎯"
# Telekom Ecommerce - AI-Powered Voice Assistant

A modern telekom.de-like ecommerce website with intelligent voice assistant powered by OpenAI GPT-4o-mini.

## 🌟 Features

- **Smart Voice Assistant**: Natural conversation with speech recognition (Hindi + English)  
- **AI-Powered Search**: Intelligent product recommendations using GPT-4o-mini
- **Context Awareness**: Remembers conversation history and understands references
- **Speech Error Correction**: Handles speech recognition errors intelligently
- **Full Ecommerce**: Device catalog, mobile plans, shopping cart, checkout
- **Professional UI**: Modern Telekom branding with responsive design

## 🛠 Tech Stack

- **Frontend**: React 18, Tailwind CSS, shadcn/ui components
- **Backend**: FastAPI, Python 3.8+
- **Database**: MongoDB
- **AI**: OpenAI GPT-4o-mini via emergentintegrations
- **Voice**: Web Speech API (speech recognition + synthesis)

## 📋 Prerequisites

- **Node.js** 18+ and npm/yarn
- **Python** 3.8+
- **MongoDB** (local or cloud)
- **OpenAI API Key** (for smart assistant features)

## 🚀 Setup Instructions

### 1. Clone/Extract the Project
```bash
cd telekom-ecommerce
```

### 2. Backend Setup

```bash
# Navigate to backend-copy directory
cd backend-copy

# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables
# Edit backend-copy/.env and add your OpenAI API key:
OPENAI_API_KEY="your-openai-api-key-here"
```

### 3. Frontend Setup

```bash
# Navigate to frontend directory (from project root)
cd frontend

# Install dependencies
npm install
# or
yarn install
```

### 4. Database Setup

**Option A: Local MongoDB**
```bash
# Install MongoDB locally
# Ubuntu/Debian:
sudo apt-get install mongodb

# macOS:
brew install mongodb

# Start MongoDB service
sudo systemctl start mongodb
# or on macOS:
brew services start mongodb
```

**Option B: MongoDB Atlas (Cloud)**
1. Create account at https://www.mongodb.com/atlas
2. Create a free cluster
3. Get connection string
4. Update `MONGO_URL` in `backend/.env`

### 5. Start the Application

**Terminal 1 - Backend:**
```bash
cd backend-copy
python server.py
```
Backend will run on: http://localhost:8001

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
# or
yarn start
```
Frontend will run on: http://localhost:3000

## 🔑 Configuration

### Backend Environment (.env)
```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="telekom_ecommerce"
OPENAI_API_KEY="your-openai-api-key-here"
LLM_MODEL="gpt-4o-mini"
```

### Frontend Environment (.env)
```env
REACT_APP_BACKEND_URL="http://localhost:8001"
```

## 🎤 Voice Assistant Usage

1. **Click search bar** to open chat interface
2. **Click microphone icon** to start voice mode
3. **Speak naturally**: "Show me iPhone options"
4. **AI responds** and automatically starts listening again
5. **Continue conversation**: "Add the iPhone to cart"
6. **Click minimize (-)** to return to search bar

### Voice Commands Examples:
- "Show me S plan" (works even if recognized as "ESP plan")
- "I want a budget phone under 700 euros"
- "Add iPhone to cart"
- "Compare MagentaMobil plans"
- "Show my cart"

## 🛒 Product Catalog

### Featured Devices:
- iPhone 15 Pro - €999.99
- Samsung Galaxy S24 Ultra - €899.99  
- Google Pixel 8 - €699.99

### Mobile Plans:
- MagentaMobil XS - €19.99/month (2GB)
- MagentaMobil S - €29.99/month (6GB)
- MagentaMobil M - €39.99/month (15GB) - Most Popular
- MagentaMobil L - €59.99/month (Unlimited)
- MagentaMobil XL - €79.99/month (Premium)
- MagentaMobil Business - €49.99/month (25GB + Business features)

## 🔧 Development

### API Endpoints:
- `GET /api/devices` - Get all devices
- `GET /api/plans` - Get all plans
- `POST /api/search` - Text search with AI
- `POST /api/voice-search` - Voice search with context

### Key Components:
- **Smart Search Bar**: Expands into chat interface
- **Voice Recognition**: Continuous conversation mode
- **Context Management**: Preserves chat history and search results
- **Speech Error Correction**: Intelligent LLM-based corrections

## 🎯 Features in Detail

### Voice Assistant Intelligence:
- **Speech Recognition**: Web Speech API with Hindi/English support
- **Error Correction**: "ESP plan" → "S plan", "I phone" → "iPhone"
- **Context Awareness**: Remembers previous search results
- **Natural Conversation**: No need to repeat context

### UI/UX Features:
- **Minimize Button**: Returns chat to search bar
- **History Preservation**: Chat history persists across sessions
- **Smart Responses**: AI speaks concise, relevant information
- **Click Outside**: Closes chat when clicking elsewhere

## 🐛 Troubleshooting

### Common Issues:

**Voice not working:**
- Ensure browser supports Web Speech API (Chrome recommended)
- Check microphone permissions
- Verify HTTPS (required for speech recognition)

**AI not responding:**
- Check OpenAI API key in backend/.env
- Verify backend is running on port 8001
- Check browser console for errors

**Database errors:**
- Ensure MongoDB is running
- Check connection string in .env
- Verify database permissions

**Frontend build errors:**
- Delete node_modules and reinstall: `rm -rf node_modules && npm install`
- Check Node.js version (18+ required)

## 📱 Browser Support

- **Chrome**: Full support (recommended)
- **Firefox**: Limited voice support
- **Safari**: Basic functionality
- **Edge**: Good support

## 🎨 Customization

### Adding New Products:
1. Edit `sample_devices` or `sample_plans` in `backend/server.py`
2. Restart backend server
3. Products will auto-populate in database

### Styling:
- Edit `frontend/src/App.css` for custom styles
- Modify `frontend/tailwind.config.js` for Tailwind customization
- Update colors in CSS variables for theme changes

## 📄 License

This project is for demonstration purposes. Telekom branding used for educational/portfolio purposes only.

## 🤝 Support

For issues or questions:
1. Check troubleshooting section above
2. Verify all prerequisites are installed
3. Ensure API keys are correctly configured
4. Check browser console for error messages

## 🚀 Deployment

For production deployment:
1. Set up production MongoDB
2. Configure production environment variables
3. Build frontend: `npm run build`
4. Deploy backend to your preferred hosting service
5. Ensure HTTPS for voice features

---

**Built with ❤️ using React, FastAPI, and OpenAI**

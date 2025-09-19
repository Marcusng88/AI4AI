# AI4AI Chat Interface

A simple ChatGPT-like interface built with Streamlit for the AI4AI project.

## Features

- 🤖 Clean, modern chat interface
- 💬 Real-time messaging
- 📱 Responsive design
- 🎨 Custom styling
- 📊 Chat statistics
- 🧹 Clear chat functionality

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
streamlit run app.py
```

3. Open your browser and navigate to `http://localhost:8501`

## Project Structure

```
AI4AI/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── README.md          # This file
└── backend/           # Backend code (to be integrated)
    └── main.py
```

## Next Steps

- [ ] Integrate with AI backend
- [ ] Add streaming responses
- [ ] Implement conversation memory
- [ ] Add file upload support
- [ ] Add user authentication

## Development

The interface is ready for backend integration. The chat messages are stored in `st.session_state.messages` and can be easily connected to your AI service.

## License

See LICENSE file for details.

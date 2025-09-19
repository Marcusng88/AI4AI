# AI-Enhanced Government Services Backend

A FastAPI-based backend for the AI-Enhanced Government Services platform, providing multi-agent orchestration for Malaysian government services.

## 🏗️ Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py              # Application configuration
│   ├── core/
│   │   ├── __init__.py
│   │   └── logging.py         # Logging configuration
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py        # Request models
│   │   └── responses.py       # Response models
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py          # Health check endpoints
│   │   ├── chat.py            # Chat endpoints
│   │   └── agents.py          # Agent management endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── chat_service.py    # Chat business logic
│   │   └── agent_service.py   # Agent management logic
│   └── agents/
│       ├── __init__.py
│       └── coordinator.py     # Coordinator agent implementation
├── agents/                    # Legacy agent directories (to be migrated)
├── requirements.txt           # Python dependencies
├── env.example               # Environment variables template
├── run.py                    # Simple run script
└── README.md                 # This file
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit .env with your configuration
# At minimum, set your AWS credentials and API keys
```

### 3. Run the Application

```bash
# Option 1: Using the run script
python run.py

# Option 2: Using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Access the API

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/v1/health

## 📚 API Endpoints

### Health Check
- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed health check

### Chat
- `POST /api/v1/chat` - Send message to AI agents
- `GET /api/v1/chat/sessions/{session_id}/history` - Get chat history
- `DELETE /api/v1/chat/sessions/{session_id}` - Clear chat session

### Agents
- `GET /api/v1/agents` - List all agents
- `GET /api/v1/agents/{agent_name}` - Get agent status
- `POST /api/v1/agents/{agent_name}/restart` - Restart agent

## 🤖 Multi-Agent Architecture

### Coordinator Agent (Active)
- **Role**: Central orchestrator and intent recognition
- **Capabilities**: Intent classification, task routing, session management
- **Status**: ✅ Implemented and active

### Sub-Agents (Phase 2-3)
- **Website Researcher Agent**: Government website discovery
- **Information Gather Agent**: Credential and requirement analysis  
- **Crawler Agent**: Website crawling and analysis (Phase 3)
- **Automation Agent**: Navigation and link extraction

## 🧪 Testing the API

### Example Chat Request

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "Saya nak bayar saman JPJ",
       "language": "ms",
       "session_id": "test-session-123"
     }'
```

### Example Response

```json
{
  "message": "Saya akan membantu anda bayar saman JPJ. Sila berikan nombor IC dan nombor plat kenderaan anda.",
  "session_id": "test-session-123",
  "status": "success",
  "metadata": {
    "intent": "jpj_summons",
    "next_action": "collect_credentials",
    "required_info": ["ic_number", "license_plate"],
    "agency": "jpj"
  }
}
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AWS_DEFAULT_REGION` | AWS region for services | Yes |
| `AWS_ACCESS_KEY_ID` | AWS access key | Yes |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Yes |
| `BEDROCK_MODEL_ID` | Bedrock model to use | Yes |
| `STRANDS_API_KEY` | Strands SDK API key | Yes |
| `TAVILY_API_KEY` | Tavily search API key | Phase 2 |
| `DEBUG` | Enable debug mode | No |

### Malaysian Government Services

The system is configured for these Malaysian government agencies:

- **JPJ** (Jabatan Pengangkutan Jalan): License renewal, summons payment
- **LHDN** (Lembaga Hasil Dalam Negeri): Tax filing assistance
- **JPN** (Jabatan Pendaftaran Negara): MyKad services
- **EPF** (Employees Provident Fund): Account inquiries

## 🏗️ Development

### Code Style

```bash
# Format code
black app/

# Sort imports
isort app/

# Lint code
flake8 app/
```

### Testing

```bash
# Run tests (when implemented)
pytest

# Run with coverage
pytest --cov=app
```

## 📝 Logging

Logs are written to:
- **Console**: Colored output with timestamps
- **File**: `logs/app.log` with rotation

Log levels can be configured via `LOG_LEVEL` environment variable.

## 🚀 Deployment

### AWS Deployment (Future)

The application is designed for deployment on AWS with:
- **ECS/Fargate**: Container orchestration
- **Application Load Balancer**: Traffic distribution
- **RDS**: Database (when implemented)
- **CloudWatch**: Monitoring and logging

### Docker (Future)

```dockerfile
# Dockerfile will be added in future phases
FROM python:3.11-slim
# ... deployment configuration
```

## 🔮 Next Steps

### Phase 2 (Months 4-6)
- [ ] Implement Website Researcher Agent
- [ ] Implement Information Gather Agent
- [ ] Add vector database integration
- [ ] Implement basic automation workflows

### Phase 3 (Months 7-9)
- [ ] Implement Crawler Agent
- [ ] Enhanced automation capabilities
- [ ] WhatsApp Business API integration
- [ ] Production deployment

## 📞 Support

For questions or issues:
1. Check the API documentation at `/docs`
2. Review the health check endpoint
3. Check application logs in `logs/app.log`

## 📄 License

See LICENSE file for details.

# AI4AI - AI-Enhanced Government Services Platform

A comprehensive full-stack application that provides AI-powered assistance for Malaysian government services through a multi-agent architecture. The platform features a modern Next.js frontend with AWS Amplify authentication and a FastAPI backend with intelligent automation capabilities.

## 🏗️ Architecture Overview

### Frontend (Next.js + TypeScript)
- **Framework**: Next.js 15.5.3 with App Router
- **UI Library**: Radix UI components with Tailwind CSS
- **Authentication**: AWS Cognito via Amplify
- **Styling**: Tailwind CSS with custom design system
- **State Management**: React hooks and context

### Backend (FastAPI + Python)
- **Framework**: FastAPI with async/await support
- **AI Integration**: AWS Bedrock (Claude 3.5 Sonnet)
- **Database**: DynamoDB for chat persistence
- **Multi-Agent System**: CrewAI-based automation agents
- **Browser Automation**: Playwright for web interactions
- **Authentication**: JWT-based with AWS Cognito integration

### Deployment
- **Frontend**: AWS Amplify with automatic deployments
- **Backend**: Docker containerization ready for AWS ECS/Fargate
- **Infrastructure**: AWS services (Cognito, DynamoDB, Bedrock)

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ and **pnpm** (recommended) or npm
- **Python** 3.11+
- **AWS Account** with appropriate permissions
- **Git** for version control

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd AI4AI
```

### 2. Backend Setup

#### 2.1 Create Virtual Environment

```bash
cd backend
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

#### 2.2 Install Dependencies

```bash
pip install -r requirements.txt
```

#### 2.3 Configure Environment Variables

```bash
# Copy the environment template
cp env.example .env

# Edit .env with your configuration
```

**Required Environment Variables:**

```env
# AWS Configuration
DEFAULT_AWS_REGION=ap-southeast-2
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# DynamoDB Tables
DYNAMODB_CHAT_SESSIONS_TABLE=ai4ai-chat-sessions
DYNAMODB_CHAT_MESSIONS_TABLE=ai4ai-chat-messages

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_AGENT_CORE_REGION=us-west-2

# API Keys
NOVA_ACT_API_KEY=your_nova_act_api_key
STRANDS_API_KEY=your_strands_api_key
TAVILY_API_KEY=your_tavily_api_key

# Security
SECRET_KEY=your-secret-key-here
```

#### 2.4 Run the Backend

```bash
# Option 1: Using the run script
python run.py

# Option 2: Using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will be available at:
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

### 3. Frontend Setup

#### 3.1 Install Dependencies

```bash
cd frontend
pnpm install
# or
npm install
```

#### 3.2 Configure Amplify Authentication

The frontend is pre-configured with AWS Cognito settings for the `ap-southeast-5` region. If you need to use different settings, update `frontend/lib/amplify-config.ts`:

```typescript
const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: 'your-user-pool-id',
      userPoolClientId: 'your-client-id',
      // ... other configuration
    }
  }
}
```

#### 3.3 Run the Frontend

```bash
pnpm dev
# or
npm run dev
```

The frontend will be available at http://localhost:3000

## 🔧 Configuration Details

### AWS Services Setup

#### 1. DynamoDB Tables

Create the following tables in your AWS account:

**Table: `ai4ai-chat-sessions`**
- Partition Key: `session_id` (String)
- Sort Key: `user_id` (String)

**Table: `ai4ai-chat-messages`**
- Partition Key: `session_id` (String)
- Sort Key: `timestamp` (Number)

#### 2. AWS Cognito User Pool

Create a Cognito User Pool with:
- **App Client**: SPA (Single Page Application)
- **OAuth Flows**: Authorization Code Grant
- **Callback URLs**: 
  - `http://localhost:3000/auth/callback` (development)
  - `https://your-domain.amplifyapp.com/auth/callback` (production)

#### 3. AWS Bedrock

Ensure you have access to the Claude 3.5 Sonnet model in the `ap-southeast-2` region.

### Environment Variables Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key for DynamoDB/Bedrock | Yes | - |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Yes | - |
| `DEFAULT_AWS_REGION` | AWS region for services | Yes | `ap-southeast-2` |
| `BEDROCK_MODEL_ID` | Bedrock model to use | Yes | `anthropic.claude-3-5-sonnet-20241022-v2:0` |
| `NOVA_ACT_API_KEY` | Nova Act API key for automation | Yes | - |
| `STRANDS_API_KEY` | Strands SDK API key | Yes | - |
| `TAVILY_API_KEY` | Tavily search API key | No | - |
| `CORS_ORIGINS` | Allowed CORS origins | No | `http://localhost:3000` |
| `DEBUG` | Enable debug mode | No | `True` |

## 🤖 Multi-Agent Architecture

### Coordinator Agent
- **Role**: Central orchestrator and intent recognition
- **Capabilities**: Intent classification, task routing, session management
- **Status**: ✅ Active and implemented

### Automation Agent
- **Role**: Web automation and task execution
- **Capabilities**: Browser automation, form filling, data extraction
- **Tools**: Playwright, CrewAI, Nova Act API
- **Status**: ✅ Active and implemented

### Validator Agent
- **Role**: Task validation and quality assurance
- **Capabilities**: Result validation, error handling, retry logic
- **Status**: ✅ Active and implemented

## 📱 Features

### Frontend Features
- 🔐 **Authentication**: AWS Cognito integration with OAuth
- 💬 **Real-time Chat**: WebSocket-based messaging
- 🎨 **Modern UI**: Radix UI components with Tailwind CSS
- 📱 **Responsive Design**: Mobile-first approach
- 🌙 **Dark Mode**: Theme switching support
- 🔄 **Real-time Updates**: Live chat status and typing indicators

### Backend Features
- 🤖 **Multi-Agent System**: Intelligent task orchestration
- 🌐 **Web Automation**: Browser-based government service interaction
- 💾 **Data Persistence**: DynamoDB for chat history
- 🔍 **Search Integration**: Tavily API for web search
- 📊 **Health Monitoring**: Comprehensive health checks
- 🔒 **Security**: JWT authentication and CORS protection

### Government Services Integration
- **JPJ** (Jabatan Pengangkutan Jalan): License renewal, summons payment
- **LHDN** (Lembaga Hasil Dalam Negeri): Tax filing assistance
- **JPN** (Jabatan Pendaftaran Negara): MyKad services
- **EPF** (Employees Provident Fund): Account inquiries

## 🚀 Deployment

### Frontend Deployment (AWS Amplify)

1. **Connect Repository**: Link your GitHub repository to AWS Amplify
2. **Configure Build**: The `amplify.yml` file is already configured
3. **Environment Variables**: Set any required environment variables in Amplify console
4. **Deploy**: Amplify will automatically build and deploy your frontend

### Backend Deployment (Docker + AWS ECS)

1. **Build Docker Image**:
   ```bash
   cd backend
   docker build -t ai4ai-backend .
   ```

2. **Push to ECR**:
   ```bash
   aws ecr create-repository --repository-name ai4ai-backend
   docker tag ai4ai-backend:latest <account-id>.dkr.ecr.<region>.amazonaws.com/ai4ai-backend:latest
   docker push <account-id>.dkr.ecr.<region>.amazonaws.com/ai4ai-backend:latest
   ```

3. **Deploy to ECS**: Create ECS service with the container image

## 🧪 Testing

### Backend API Testing

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Chat endpoint
curl -X POST "http://localhost:8000/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "Saya nak bayar saman JPJ",
       "language": "ms",
       "session_id": "test-session-123"
     }'
```

### Frontend Testing

```bash
cd frontend
pnpm test
# or
npm test
```

## 📁 Project Structure

```
AI4AI/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── agents/            # Multi-agent system
│   │   │   ├── automation/    # Web automation agent
│   │   │   ├── coordinator/   # Central coordinator
│   │   │   └── validator/     # Task validation
│   │   ├── core/              # Core utilities
│   │   ├── middleware/        # Authentication middleware
│   │   ├── models/            # Pydantic models
│   │   ├── routers/           # API endpoints
│   │   └── services/          # Business logic
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile            # Container configuration
│   └── env.example           # Environment template
├── frontend/                  # Next.js frontend
│   ├── app/                  # App Router pages
│   ├── components/           # React components
│   │   ├── auth/            # Authentication components
│   │   ├── browser/         # Browser automation UI
│   │   ├── chat/            # Chat interface
│   │   └── ui/              # Reusable UI components
│   ├── hooks/               # Custom React hooks
│   ├── lib/                 # Utilities and configurations
│   ├── package.json         # Node.js dependencies
│   └── next.config.mjs      # Next.js configuration
├── amplify.yml              # Amplify deployment config
└── README.md               # This file
```

## 🔧 Development

### Code Style

**Backend (Python)**:
```bash
# Format code
black app/

# Sort imports
isort app/

# Lint code
flake8 app/
```

**Frontend (TypeScript)**:
```bash
# Lint and fix
pnpm lint

# Type check
pnpm type-check
```

### Adding New Features

1. **Backend**: Add new routers in `app/routers/` and services in `app/services/`
2. **Frontend**: Add new pages in `app/` and components in `components/`
3. **Agents**: Extend the multi-agent system in `app/agents/`

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Error**:
   - Ensure AWS credentials are properly configured
   - Check DynamoDB table permissions
   - Verify region settings

2. **Authentication Issues**:
   - Verify Cognito User Pool configuration
   - Check callback URLs in Amplify config
   - Ensure CORS settings are correct

3. **Agent Initialization Errors**:
   - Check API keys for external services
   - Verify Bedrock model access
   - Review agent logs in `logs/app.log`

### Logs

- **Backend Logs**: `backend/logs/app.log`
- **Frontend Logs**: Browser console and network tab
- **Agent Logs**: Check individual agent output in backend logs

## 📞 Support

For issues and questions:

1. Check the API documentation at `/docs`
2. Review the health check endpoint
3. Check application logs
4. Verify environment configuration

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **AWS Bedrock** for AI capabilities
- **CrewAI** for multi-agent orchestration
- **Next.js** and **FastAPI** for the robust framework
- **Radix UI** for accessible component library
- **Malaysian Government** for service integration opportunities

---

**Built with ❤️ for Malaysian citizens to simplify government service interactions**

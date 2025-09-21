"""DynamoDB service for chat session and message management."""

import boto3
import aioboto3
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import uuid
from botocore.exceptions import ClientError, NoCredentialsError
from app.config import settings
from app.core.logging import logger


class DynamoDBService:
    """Service for managing chat sessions and messages in DynamoDB."""
    
    def __init__(self):
        """Initialize DynamoDB service."""
        self.region = settings.aws_region
        self.sessions_table = settings.dynamodb_chat_sessions_table
        self.messages_table = settings.dynamodb_chat_messages_table
        
        # Session for aioboto3 (async operations)
        self.session = aioboto3.Session()
        
        # Regular boto3 client for sync operations
        self._sync_client = None
        
    @property
    def sync_client(self):
        """Get synchronous DynamoDB client."""
        if self._sync_client is None:
            self._sync_client = boto3.client(
                'dynamodb',
                region_name=self.region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
        return self._sync_client
    
    async def get_async_client(self):
        """Get asynchronous DynamoDB client."""
        return self.session.client(
            'dynamodb',
            region_name=self.region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
    
    async def create_tables_if_not_exist(self):
        """Create DynamoDB tables if they don't exist."""
        try:
            # Quick check for AWS credentials first
            if not settings.aws_access_key_id or not settings.aws_secret_access_key:
                logger.warning("AWS credentials not configured. DynamoDB will not be available.")
                logger.warning("Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY to enable DynamoDB.")
                return
            
            logger.info("Initializing DynamoDB connection...")
            
            # Add timeout to prevent hanging
            import asyncio
            try:
                async with asyncio.timeout(10):  # 10 second timeout
                    async with await self.get_async_client() as client:
                        # Check if sessions table exists
                        try:
                            await client.describe_table(TableName=self.sessions_table)
                            logger.info(f"Sessions table {self.sessions_table} already exists")
                        except ClientError as e:
                            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                                await self._create_sessions_table(client)
                            else:
                                raise
                        
                        # Check if messages table exists
                        try:
                            await client.describe_table(TableName=self.messages_table)
                            logger.info(f"Messages table {self.messages_table} already exists")
                        except ClientError as e:
                            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                                await self._create_messages_table(client)
                            else:
                                raise
                                
            except asyncio.TimeoutError:
                logger.error("DynamoDB connection timed out. Check your AWS region and credentials.")
                raise
                        
        except NoCredentialsError:
            logger.error("AWS credentials not configured. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
            raise
        except Exception as e:
            logger.error(f"Error creating DynamoDB tables: {e}")
            raise
    
    async def _create_sessions_table(self, client):
        """Create the chat sessions table."""
        logger.info(f"Creating sessions table: {self.sessions_table}")
        
        table_definition = {
            'TableName': self.sessions_table,
            'KeySchema': [
                {
                    'AttributeName': 'user_id',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'session_id',
                    'KeyType': 'RANGE'
                }
            ],
            'AttributeDefinitions': [
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'session_id',
                    'AttributeType': 'S'
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        }
        
        await client.create_table(**table_definition)
        logger.info(f"Sessions table {self.sessions_table} created successfully")
    
    async def _create_messages_table(self, client):
        """Create the chat messages table."""
        logger.info(f"Creating messages table: {self.messages_table}")
        
        table_definition = {
            'TableName': self.messages_table,
            'KeySchema': [
                {
                    'AttributeName': 'session_id',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'created_at',
                    'KeyType': 'RANGE'
                }
            ],
            'AttributeDefinitions': [
                {
                    'AttributeName': 'session_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'created_at',
                    'AttributeType': 'S'
                }
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        }
        
        await client.create_table(**table_definition)
        logger.info(f"Messages table {self.messages_table} created successfully")
    
    async def create_session(self, user_id: str, title: str = None) -> Dict[str, Any]:
        """Create a new chat session."""
        # Check if AWS credentials are available
        if not settings.aws_access_key_id or not settings.aws_secret_access_key:
            raise Exception("DynamoDB not available: AWS credentials not configured")
        
        session_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        session_data = {
            'user_id': {'S': user_id},
            'session_id': {'S': session_id},
            'title': {'S': title or f"Chat Session {created_at.strftime('%Y-%m-%d %H:%M')}"},
            'created_at': {'S': created_at.isoformat()},
            'updated_at': {'S': created_at.isoformat()},
            'message_count': {'N': '0'}
        }
        
        try:
            import asyncio
            async with asyncio.timeout(5):  # 5 second timeout for operations
                async with await self.get_async_client() as client:
                    await client.put_item(
                        TableName=self.sessions_table,
                        Item=session_data
                    )
            
            logger.info(f"Created session {session_id} for user {user_id}")
            return {
                'session_id': session_id,
                'user_id': user_id,
                'title': session_data['title']['S'],
                'created_at': session_data['created_at']['S'],
                'updated_at': session_data['updated_at']['S'],
                'message_count': 0
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout creating session for user {user_id}")
            raise Exception("DynamoDB operation timed out")
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise
    
    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user."""
        # Check if AWS credentials are available
        if not settings.aws_access_key_id or not settings.aws_secret_access_key:
            raise Exception("DynamoDB not available: AWS credentials not configured")
            
        try:
            import asyncio
            async with asyncio.timeout(5):  # 5 second timeout
                async with await self.get_async_client() as client:
                    response = await client.query(
                        TableName=self.sessions_table,
                        KeyConditionExpression='user_id = :user_id',
                        ExpressionAttributeValues={
                            ':user_id': {'S': user_id}
                        },
                        ScanIndexForward=False  # Sort by session_id descending (newest first)
                    )
                
                sessions = []
                for item in response.get('Items', []):
                    session = {
                        'session_id': item['session_id']['S'],
                        'user_id': item['user_id']['S'],
                        'title': item['title']['S'],
                        'created_at': item['created_at']['S'],
                        'updated_at': item['updated_at']['S'],
                        'message_count': int(item.get('message_count', {'N': '0'})['N'])
                    }
                    sessions.append(session)
                
                return sessions
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout getting sessions for user {user_id}")
            raise Exception("DynamoDB operation timed out")
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            raise
    
    async def get_session(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific session."""
        try:
            async with await self.get_async_client() as client:
                response = await client.get_item(
                    TableName=self.sessions_table,
                    Key={
                        'user_id': {'S': user_id},
                        'session_id': {'S': session_id}
                    }
                )
            
            if 'Item' not in response:
                return None
            
            item = response['Item']
            return {
                'session_id': item['session_id']['S'],
                'user_id': item['user_id']['S'],
                'title': item['title']['S'],
                'created_at': item['created_at']['S'],
                'updated_at': item['updated_at']['S'],
                'message_count': int(item.get('message_count', {'N': '0'})['N'])
            }
            
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            raise
    
    async def add_message(self, session_id: str, role: str, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add a message to a session."""
        created_at = datetime.utcnow().isoformat()
        message_id = str(uuid.uuid4())
        
        message_data = {
            'session_id': {'S': session_id},
            'created_at': {'S': created_at},
            'message_id': {'S': message_id},
            'role': {'S': role},  # 'user', 'assistant', 'system'
            'content': {'S': content}
        }
        
        if metadata:
            message_data['metadata'] = {'S': json.dumps(metadata)}
        
        try:
            async with await self.get_async_client() as client:
                # Add the message
                await client.put_item(
                    TableName=self.messages_table,
                    Item=message_data
                )
            
            logger.info(f"Added message {message_id} to session {session_id}")
            return {
                'message_id': message_id,
                'session_id': session_id,
                'role': role,
                'content': content,
                'created_at': created_at,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            raise
    
    async def get_session_messages(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get messages for a session."""
        try:
            async with await self.get_async_client() as client:
                query_params = {
                    'TableName': self.messages_table,
                    'KeyConditionExpression': 'session_id = :session_id',
                    'ExpressionAttributeValues': {
                        ':session_id': {'S': session_id}
                    },
                    'ScanIndexForward': True,  # Sort by created_at ascending (oldest first)
                    'Limit': limit
                }
                
                response = await client.query(**query_params)
            
            messages = []
            for item in response.get('Items', []):
                message = {
                    'message_id': item['message_id']['S'],
                    'session_id': item['session_id']['S'],
                    'role': item['role']['S'],
                    'content': item['content']['S'],
                    'created_at': item['created_at']['S']
                }
                
                if 'metadata' in item:
                    try:
                        message['metadata'] = json.loads(item['metadata']['S'])
                    except json.JSONDecodeError:
                        message['metadata'] = {}
                
                messages.append(message)
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting session messages: {e}")
            raise
    
    async def update_session(self, user_id: str, session_id: str, title: str = None) -> bool:
        """Update session information."""
        try:
            update_expression = "SET updated_at = :updated_at"
            expression_values = {
                ':updated_at': {'S': datetime.utcnow().isoformat()}
            }
            
            if title:
                update_expression += ", title = :title"
                expression_values[':title'] = {'S': title}
            
            async with await self.get_async_client() as client:
                await client.update_item(
                    TableName=self.sessions_table,
                    Key={
                        'user_id': {'S': user_id},
                        'session_id': {'S': session_id}
                    },
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expression_values
                )
            
            logger.info(f"Updated session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating session: {e}")
            return False
    
    async def delete_session(self, user_id: str, session_id: str) -> bool:
        """Delete a session and all its messages."""
        try:
            # Validate inputs
            if not user_id or not isinstance(user_id, str):
                logger.error(f"Invalid user_id: {user_id} (type: {type(user_id)})")
                return False
            if not session_id or not isinstance(session_id, str):
                logger.error(f"Invalid session_id: {session_id} (type: {type(session_id)})")
                return False
                
            logger.info(f"Deleting session {session_id} for user {user_id}")
            
            async with await self.get_async_client() as client:
                # First, get all messages for this session
                messages_response = await client.query(
                    TableName=self.messages_table,
                    KeyConditionExpression='session_id = :session_id',
                    ExpressionAttributeValues={
                        ':session_id': {'S': session_id}
                    }
                )
                
                # Delete all messages
                for item in messages_response.get('Items', []):
                    try:
                        delete_key = {
                            'session_id': {'S': session_id},
                            'created_at': {'S': item['created_at']['S']}
                        }
                        logger.debug(f"Deleting message with key: {delete_key}")
                        await client.delete_item(
                            TableName=self.messages_table,
                            Key=delete_key
                        )
                    except Exception as e:
                        logger.error(f"Error deleting message: {e}")
                        logger.error(f"Message item: {item}")
                        raise
                
                # Delete the session
                try:
                    session_delete_key = {
                        'user_id': {'S': user_id},
                        'session_id': {'S': session_id}
                    }
                    logger.debug(f"Deleting session with key: {session_delete_key}")
                    await client.delete_item(
                        TableName=self.sessions_table,
                        Key=session_delete_key
                    )
                except Exception as e:
                    logger.error(f"Error deleting session: {e}")
                    logger.error(f"Session delete key: {session_delete_key}")
                    raise
            
            logger.info(f"Deleted session {session_id} and all messages")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False


# Global service instance
dynamodb_service = DynamoDBService()

# MedIQ Chat API Integration Guide

This guide explains how to integrate with the MedIQ Chat API from your frontend application.

## Overview of Chat Features

The MedIQ Chat system provides an AI-powered medical assistant that can help users understand their medical documents, analyze symptoms, and provide health information. Key features include:

- **Chat Sessions**: Create and manage separate conversations with the AI
- **Document Context**: Reference medical documents in your conversations
- **Message History**: Store and retrieve conversation history
- **Medical Insights**: Extract relevant medical information

## API Endpoints

### Chat with AI

```
POST /chat/chat
```

This is the main endpoint for sending messages to the AI assistant.

**Request Body:**
```json
{
  "session_id": "optional-uuid-for-existing-session",
  "user_message": "What does this blood test result mean?",
  "document_text": "Patient shows elevated white blood cell count of 12,000/μL",
  "include_document_context": true
}
```

**Response:**
```json
{
  "session_id": "uuid-of-session",
  "response": "An elevated white blood cell count (12,000/μL) typically indicates that your body is fighting an infection...",
  "user_message_id": "uuid-of-user-message",
  "assistant_message_id": "uuid-of-assistant-message",
  "is_new_session": false
}
```

### Session Management

#### List All Sessions

```
GET /chat/sessions
```

Returns all chat sessions for the current user.

**Response:**
```json
[
  {
    "id": "session-uuid",
    "user_id": "username",
    "title": "Blood Test Discussion",
    "started_at": "2023-05-15T10:30:00",
    "ended_at": null,
    "document_id": "optional-document-uuid",
    "last_message": "What does my blood test show?"
  }
]
```

#### Create New Session

```
POST /chat/sessions
```

Creates a new chat session.

**Request Body:**
```json
{
  "title": "Discuss Recent MRI Results",
  "document_id": "optional-document-uuid"
}
```

**Response:**
```json
{
  "session_id": "new-session-uuid",
  "session": {
    "id": "new-session-uuid",
    "user_id": "username",
    "title": "Discuss Recent MRI Results",
    "started_at": "2023-05-15T10:30:00",
    "document_id": "optional-document-uuid"
  }
}
```

#### Get Session Details

```
GET /chat/sessions/{session_id}
```

Returns details about a specific chat session.

**Response:**
```json
{
  "id": "session-uuid",
  "user_id": "username",
  "title": "Blood Test Discussion",
  "started_at": "2023-05-15T10:30:00",
  "ended_at": null,
  "document_id": "optional-document-uuid",
  "last_message": "What does my blood test show?"
}
```

#### Update Session

```
PUT /chat/sessions/{session_id}
```

Updates a chat session's title or ends the session.

**Request Body:**
```json
{
  "title": "Updated Title",
  "ended_at": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Chat session updated successfully"
}
```

#### Get Session History

```
GET /chat/sessions/{session_id}/history?limit=50&offset=0
```

Returns the message history for a specific chat session.

**Response:**
```json
[
  {
    "id": "message-uuid",
    "session_id": "session-uuid",
    "role": "user",
    "content": "What does my blood test show?",
    "created_at": "2023-05-15T10:31:00"
  },
  {
    "id": "message-uuid",
    "session_id": "session-uuid",
    "role": "assistant",
    "content": "Your blood test shows normal levels for most markers...",
    "created_at": "2023-05-15T10:31:05"
  }
]
```

#### Delete Session

```
DELETE /chat/sessions/{session_id}
```

Deletes a chat session and all its messages.

**Response:**
```json
{
  "success": true,
  "message": "Chat session deleted successfully"
}
```

## Frontend Integration Examples

### JavaScript Examples

#### Creating a Chat Session

```javascript
async function createChatSession(title, documentId = null) {
  const response = await fetch('https://your-api-url/chat/sessions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${userToken}`
    },
    body: JSON.stringify({
      title: title,
      document_id: documentId
    })
  });
  
  const data = await response.json();
  return data.session_id;
}
```

#### Sending a Message

```javascript
async function sendMessage(sessionId, message, documentText = null) {
  const response = await fetch('https://your-api-url/chat/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${userToken}`
    },
    body: JSON.stringify({
      session_id: sessionId,
      user_message: message,
      document_text: documentText,
      include_document_context: true
    })
  });
  
  return await response.json();
}
```

#### Getting Chat History

```javascript
async function getChatHistory(sessionId, limit = 50, offset = 0) {
  const response = await fetch(
    `https://your-api-url/chat/sessions/${sessionId}/history?limit=${limit}&offset=${offset}`, 
    {
      headers: {
        'Authorization': `Bearer ${userToken}`
      }
    }
  );
  
  return await response.json();
}
```

## Best Practices

1. **Create a Session Per Topic**: Create separate chat sessions for different medical topics or documents.

2. **Include Document Context**: When discussing a specific medical document, always include its text in the first message.

3. **Error Handling**: Implement proper error handling for API calls, especially for the chat endpoint which may sometimes fail if the AI model is unavailable.

4. **Session Management**: Close sessions that are no longer active by setting `ended_at` to true.

5. **Security**: Always use HTTPS and include authentication tokens in your requests.

## Environment Configuration

The chat system uses OpenRouter's API with Mistral-7B model to generate responses. Make sure your server has the `OPENROUTER_API_KEY` environment variable properly set.

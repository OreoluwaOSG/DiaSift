# DiaSift Architecture Context

## Application

DiaSift is an existing web based AI assistant focused on Type 2 diabetes information.

## Existing Behaviour
No user authentication.

A user submits a question through the web interface.

The backend processes the request through DiaSift's existing application logic.

Relevant evidence is retrieved from the existing knowledge base.

The application generates its response and presents supporting evidence/source information where appropriate.

Existing safety and scope controls must remain intact.

## Current Persistence Context

The application currently uses ChromaDB as part of its RAG knowledge retrieval implementation.

There is currently no separate relational application database specifically used for storing response feedback.

The agent should inspect the existing application before deciding how response feedback should be persisted.

## Important Constraints

Do not replace ChromaDB.

Do not redesign the existing RAG pipeline.

Do not remove existing safety controls.

Do not remove existing source/evidence functionality.

Do not expose system prompts or secret configuration.

Prefer minimal changes to unrelated functionality.

Follow the existing project architecture and conventions where practical.
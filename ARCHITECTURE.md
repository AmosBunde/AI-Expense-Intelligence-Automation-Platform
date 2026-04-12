# Architecture Diagrams

## C4 Model - Level 1: System Context

```mermaid
C4Context
    title System Context Diagram - AI Expense Intelligence Platform

    Person(employee, "Employee", "Submits expenses, views status")
    Person(manager, "Manager", "Approves/rejects expenses")
    Person(finance, "Finance Team", "Manages policies, views analytics")

    System(expensePlatform, "AI Expense Intelligence Platform", "Categorizes, analyzes, and automates business spend workflows using AI")

    System_Ext(openai, "OpenAI API", "LLM for extraction, classification, fraud detection")
    System_Ext(email, "Email Service", "SMTP for notifications")
    System_Ext(slack, "Slack", "Webhook notifications")
    System_Ext(s3, "AWS S3 / MinIO", "Document storage")
    System_Ext(banking, "Banking APIs", "Transaction data feeds")

    Rel(employee, expensePlatform, "Uploads receipts, views expenses")
    Rel(manager, expensePlatform, "Reviews flagged expenses")
    Rel(finance, expensePlatform, "Configures policies, views dashboards")
    Rel(expensePlatform, openai, "LLM inference", "HTTPS")
    Rel(expensePlatform, email, "Sends notifications", "SMTP")
    Rel(expensePlatform, slack, "Sends alerts", "Webhook")
    Rel(expensePlatform, s3, "Stores documents", "S3 API")
    Rel(banking, expensePlatform, "Feeds transactions", "API/CSV")
```

## C4 Model - Level 2: Container Diagram

```mermaid
C4Container
    title Container Diagram - AI Expense Intelligence Platform

    Person(user, "User", "Employee / Manager / Finance")

    Container_Boundary(platform, "Expense Intelligence Platform") {
        Container(gateway, "API Gateway", "FastAPI", "Auth, rate limiting, request routing")
        Container(processor, "Expense Processor", "FastAPI", "OCR, field extraction, normalization")
        Container(aiEngine, "AI Engine", "FastAPI + LangGraph", "LLM agents, RAG, fraud detection")
        Container(policyEngine, "Policy Engine", "FastAPI", "Rule evaluation, auto-approval")
        Container(dashboard, "Dashboard UI", "React + TypeScript", "Analytics, expense management")
        Container(notifier, "Notification Service", "FastAPI", "Email, Slack, webhook delivery")
        Container(batchProc, "Batch Processor", "Celery Workers", "CSV/Excel batch processing")
        ContainerDb(postgres, "PostgreSQL 16", "pgvector", "Expenses, users, policies, embeddings")
        ContainerDb(redis, "Redis 7", "Cache + Queue", "Session cache, rate limits, Celery broker")
        Container(objectStore, "Object Storage", "S3/MinIO", "Receipt images, invoices, reports")
    }

    System_Ext(openai, "OpenAI API", "GPT-4o, Embeddings")

    Rel(user, dashboard, "Uses", "HTTPS")
    Rel(dashboard, gateway, "API calls", "HTTPS/JSON")
    Rel(gateway, processor, "Process expense", "HTTP")
    Rel(gateway, aiEngine, "AI analysis", "HTTP")
    Rel(gateway, policyEngine, "Policy check", "HTTP")
    Rel(processor, aiEngine, "Extract fields", "HTTP")
    Rel(processor, policyEngine, "Check compliance", "HTTP")
    Rel(aiEngine, openai, "LLM inference", "HTTPS")
    Rel(aiEngine, postgres, "RAG retrieval", "SQL + pgvector")
    Rel(processor, postgres, "CRUD", "SQL")
    Rel(policyEngine, postgres, "Read policies", "SQL")
    Rel(gateway, redis, "Rate limit, cache", "Redis protocol")
    Rel(batchProc, redis, "Task queue", "Redis protocol")
    Rel(processor, objectStore, "Store/retrieve docs", "S3 API")
    Rel(notifier, user, "Notifications", "Email/Slack")
```

## C4 Model - Level 3: Component Diagram (AI Engine)

```mermaid
C4Component
    title Component Diagram - AI Engine

    Container_Boundary(aiEngine, "AI Engine") {
        Component(api, "FastAPI Router", "FastAPI", "HTTP endpoints: /analyze, /chat, /anomalies")
        Component(analysisGraph, "Analysis Graph", "LangGraph StateGraph", "Orchestrates extraction > RAG > fraud > categorize")
        Component(chatGraph, "Chat Graph", "LangGraph StateGraph", "Conversational agent with tool routing")
        Component(extractor, "Field Extractor", "LangChain + GPT-4o", "Extracts merchant, amount, date, category from text")
        Component(ragRetriever, "RAG Retriever", "pgvector + CrossEncoder", "Retrieves relevant policy document chunks")
        Component(fraudDetector, "Fraud Detector", "LangChain + GPT-4o", "Analyzes expense for fraud indicators")
        Component(categorizer, "Categorizer", "Python", "Refines category prediction using policy context")
        Component(tools, "Agent Tools", "LangChain Tools", "query_spend_patterns, search_similar_expenses")
        Component(embeddings, "Embedding Service", "OpenAI text-embedding-3-small", "Generates embeddings for RAG")
    }

    ContainerDb(postgres, "PostgreSQL", "pgvector")
    System_Ext(openai, "OpenAI API")

    Rel(api, analysisGraph, "Invoke analysis")
    Rel(api, chatGraph, "Invoke chat")
    Rel(analysisGraph, extractor, "Step 1: Extract")
    Rel(analysisGraph, ragRetriever, "Step 2: Retrieve policies")
    Rel(analysisGraph, fraudDetector, "Step 3: Fraud check")
    Rel(analysisGraph, categorizer, "Step 4: Categorize")
    Rel(chatGraph, tools, "Execute tools")
    Rel(extractor, openai, "GPT-4o completion")
    Rel(fraudDetector, openai, "GPT-4o completion")
    Rel(ragRetriever, embeddings, "Generate query embedding")
    Rel(ragRetriever, postgres, "Vector similarity search")
    Rel(embeddings, openai, "Embedding API")
```

## Sequence Diagram: Expense Upload Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Dashboard UI
    participant GW as API Gateway
    participant EP as Expense Processor
    participant S3 as Object Storage
    participant AI as AI Engine
    participant LLM as OpenAI GPT-4o
    participant PG as PostgreSQL
    participant PE as Policy Engine
    participant Redis as Redis
    participant Notif as Notification Service

    User->>UI: Upload receipt image
    UI->>GW: POST /api/v1/expenses/upload (JWT + file)
    GW->>GW: Validate JWT token
    GW->>Redis: Check rate limit (sliding window)
    Redis-->>GW: OK (under limit)
    GW->>EP: Forward to Expense Processor

    EP->>S3: Store document (S3 PutObject)
    S3-->>EP: file_key

    EP->>EP: OCR text extraction (Tesseract)
    EP->>AI: POST /analyze (raw_text, org_id)

    Note over AI: LangGraph Analysis Pipeline
    AI->>LLM: Extract fields (merchant, amount, date, category)
    LLM-->>AI: Structured JSON extraction
    AI->>PG: Vector search for matching policies (pgvector)
    PG-->>AI: Relevant policy chunks
    AI->>LLM: Fraud analysis (patterns, anomalies)
    LLM-->>AI: Risk assessment JSON
    AI->>AI: Categorize with policy context
    AI-->>EP: Analysis result (extraction + fraud + category)

    EP->>EP: Normalize fields (currency, dates, amounts)
    EP->>PE: POST /check (expense data + fraud result)

    Note over PE: Rule Evaluation Engine
    PE->>PE: Evaluate amount limits
    PE->>PE: Check receipt requirements
    PE->>PE: Weekend/duplicate checks
    PE->>PE: Fraud risk threshold check
    PE->>PE: Auto-approve eligibility
    PE-->>EP: PolicyCheckResult (compliant/violations/action)

    EP->>PG: INSERT expense record
    EP->>PG: INSERT policy_check record
    EP->>PG: INSERT fraud_analysis record

    alt Auto-approved
        EP->>PG: UPDATE status = 'approved'
        EP->>Notif: Notify user (approved)
    else Flagged for review
        EP->>PG: UPDATE status = 'flagged'
        EP->>Notif: Notify manager (review required)
    else Rejected
        EP->>PG: UPDATE status = 'rejected'
        EP->>Notif: Notify user (rejected with reasons)
    end

    EP-->>GW: {expense_id, status}
    GW-->>UI: 200 OK {expense_id, status, message}
    UI-->>User: Show processing result
```

## Sequence Diagram: Batch Processing Flow

```mermaid
sequenceDiagram
    autonumber
    actor Finance as Finance Team
    participant UI as Dashboard UI
    participant GW as API Gateway
    participant Redis as Redis (Celery Broker)
    participant Worker as Celery Worker
    participant EP as Expense Processor
    participant AI as AI Engine
    participant PG as PostgreSQL
    participant Notif as Notification Service

    Finance->>UI: Upload CSV batch file
    UI->>GW: POST /api/v1/batch/process (JWT + CSV)
    GW->>GW: Validate admin/finance role
    GW->>Redis: Queue batch task (Celery)
    Redis-->>GW: task_id
    GW-->>UI: {batch_id, status: "queued"}

    loop For each row in CSV
        Worker->>Redis: Dequeue task
        Worker->>EP: Process single expense
        EP->>AI: Extract + analyze
        AI-->>EP: Analysis result
        EP->>PG: Store expense
    end

    Worker->>PG: Update batch status
    Worker->>Notif: Send completion summary
    Notif-->>Finance: Email: "Batch complete: 150 processed, 12 flagged"
```

## Sequence Diagram: AI Chat Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Dashboard UI
    participant GW as API Gateway
    participant AI as AI Engine
    participant LLM as OpenAI GPT-4o
    participant PG as PostgreSQL
    participant Tools as Agent Tools

    User->>UI: "What is my top spending category this month?"
    UI->>GW: POST /api/v1/ai/chat (message, JWT)
    GW->>AI: POST /chat (message, user_id, org_id)

    Note over AI: LangGraph Chat Agent
    AI->>LLM: Process message with tool definitions
    LLM-->>AI: tool_call: query_spend_patterns(period="month", group_by="category")
    AI->>Tools: Execute query_spend_patterns
    Tools->>PG: SELECT category, SUM(amount) GROUP BY category
    PG-->>Tools: Aggregated data
    Tools-->>AI: Spend data by category
    AI->>LLM: Generate response with data
    LLM-->>AI: "Your top category is Travel at $4,230, followed by Meals at $1,890..."

    AI-->>GW: {reply, tools_used}
    GW-->>UI: Response JSON
    UI-->>User: Display AI response
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "AWS Cloud"
        subgraph "VPC"
            subgraph "Public Subnet"
                ALB[Application Load Balancer]
                NAT[NAT Gateway]
            end
            subgraph "Private Subnet - App Tier"
                ECS[ECS Cluster]
                GW[API Gateway<br>2 tasks]
                EP[Expense Processor<br>2 tasks]
                AIE[AI Engine<br>2 tasks]
                PE[Policy Engine<br>2 tasks]
                UI[Dashboard UI<br>2 tasks]
                CW[Celery Workers<br>3 tasks]
            end
            subgraph "Private Subnet - Data Tier"
                RDS[(RDS PostgreSQL 16<br>+ pgvector<br>Multi-AZ)]
                EC[(ElastiCache Redis<br>Cluster Mode)]
                S3[(S3 Bucket<br>Versioned)]
            end
        end
        CF[CloudFront CDN]
        CW2[CloudWatch<br>Monitoring]
        SM[Secrets Manager]
    end

    Users((Users)) --> CF
    CF --> ALB
    ALB --> GW
    GW --> EP
    GW --> AIE
    GW --> PE
    EP --> RDS
    EP --> S3
    AIE --> RDS
    PE --> RDS
    GW --> EC
    CW --> EC
    ECS --> CW2
    ECS --> SM

    OpenAI((OpenAI API)) -.-> AIE
```

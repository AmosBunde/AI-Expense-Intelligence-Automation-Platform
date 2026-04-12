# ADR-003: pgvector for RAG Vector Storage

**Status:** Accepted
**Date:** 2026-04-12

## Context

The AI Engine needs to retrieve relevant company policy documents when analyzing expenses. This requires storing document embeddings and performing similarity searches. Options include dedicated vector databases (Pinecone, Weaviate, Qdrant) or extending our existing PostgreSQL with pgvector.

## Decision

Use pgvector extension on PostgreSQL 16 for vector storage and similarity search.

## Rationale

- **Operational simplicity:** One database to manage instead of two. Same backup, monitoring, and scaling story.
- **Transactional consistency:** Policy documents and their embeddings live in the same transaction boundary as the expense data they relate to.
- **Metadata filtering:** SQL WHERE clauses for filtering by organization_id, document_type, and effective_date before vector search. This is critical because a query about Kenya travel policy must not return Nigeria travel policy even if semantically similar.
- **Cost:** No additional managed service fees. pgvector is free and open source.
- **Performance:** HNSW indexing in pgvector provides sub-millisecond search for our expected corpus size (tens of thousands of chunks per organization, not millions).

## Trade-offs

- **Scale ceiling:** pgvector is not optimized for billion-scale vector search. For our use case (company policy documents, not web-scale search), this ceiling is irrelevant.
- **Feature set:** Dedicated vector DBs offer more advanced features (hybrid search, automatic reindexing). We do not need these for v1.

## Implementation

- Embedding model: OpenAI `text-embedding-3-small` (1536 dimensions)
- Chunking: 512 tokens with 64-token overlap, preserving table structures
- Index: HNSW with `lists=100` for organizations with large policy corpuses
- Query pattern: Filter by `organization_id` first, then cosine similarity, then rerank with cross-encoder

## Consequences

- **Positive:** Simpler infrastructure. Joins between policy chunks and expense records. Standard PostgreSQL tooling.
- **Negative:** Must upgrade to pgvector-enabled PostgreSQL image. Cannot leverage advanced vector DB features if needed later.
- **Migration path:** If scale demands exceed pgvector capacity, extract to dedicated vector DB with minimal code changes (retriever interface remains the same).

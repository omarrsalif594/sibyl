# Scenario 1: Customer Product Q&A

## Business Problem

Acme Shop receives hundreds of product questions daily from customers shopping online. Questions range from care instructions ("Can I machine-wash this hoodie?") to technical specifications ("Is this tent waterproof?"). Customer service agents spend significant time answering repetitive questions that are already documented in product pages and FAQs.

## Solution

Implement a RAG (Retrieval-Augmented Generation) pipeline that:
1. Indexes all product documentation and FAQs as vector embeddings
2. Performs semantic search to find relevant information
3. Generates natural, accurate answers with source citations
4. Reduces response time from minutes to seconds

## Required Setup

### Data Sources
- **Product Documentation**: 12 markdown files in `data/docs/`
  - Individual product pages with specs and care instructions
  - Shipping and returns policies
  - FAQ document
  - Sizing guides

### Infrastructure
- **Vector Store**: Qdrant (local instance on port 6333)
- **Embeddings**: OpenAI text-embedding-3-small
- **LLM**: GPT-4 for answer generation

### Environment Variables
```bash
export OPENAI_API_KEY="your-key-here"
```

## Running the Pipeline

```bash
# Navigate to Acme Shop directory
cd examples/companies/acme_shop

# Run product Q&A pipeline
python pipelines/product_qa.py "Can I machine-wash this hoodie?"
```

### Example Questions

```bash
# Care instructions
python pipelines/product_qa.py "Can I machine-wash this hoodie?"
python pipelines/product_qa.py "How do I clean my hiking boots?"

# Product specifications
python pipelines/product_qa.py "Is this tent waterproof?"
python pipelines/product_qa.py "What's the temperature rating of the sleeping bag?"

# Policies
python pipelines/product_qa.py "What's your return policy?"
python pipelines/product_qa.py "Do you ship internationally?"

# Sizing
python pipelines/product_qa.py "How do I know what size backpack to get?"
```

## Expected Output

```
================================================================================
ACME SHOP - PRODUCT Q&A PIPELINE
================================================================================

Question: Can I machine-wash this hoodie?

Searching for relevant information...
Found 3 relevant chunks

Generating answer...

================================================================================
ANSWER
================================================================================
Based on the product documentation:

From alpine_hoodie.md:
# Alpine Trail Hoodie
...
**Can I machine-wash this hoodie?**
Yes! Machine wash cold with like colors. Use mild detergent. Do not bleach.

**How should I dry it?**
Tumble dry on low heat or hang to dry. Avoid high heat as it may damage the
moisture-wicking properties.

Yes, the Alpine Trail Hoodie can be machine-washed. Follow these care instructions:
- Machine wash cold with like colors
- Use mild detergent
- Do not use bleach
- Tumble dry on low heat or hang to dry
- Avoid high heat to preserve moisture-wicking properties

The hoodie is designed for easy care while maintaining its performance features.

================================================================================
SOURCES
================================================================================
  - alpine_hoodie.md
  - merino_base_layer.md
  - faq.md
```

## What's Demonstrated

### Sibyl Features
1. **Document Source Connectors**: FilesystemMarkdownSource
2. **Vector Store Integration**: Qdrant for semantic search
3. **RAG Pipeline Techniques**:
   - `rag_pipeline.chunking:markdown_chunking`
   - `rag_pipeline.embedding:sentence_transformer`
   - `rag_pipeline.retrieval:semantic_search`
   - `rag_pipeline.reranking:cross_encoder`
4. **LLM Provider Integration**: OpenAI GPT-4

### E-commerce Patterns
- Product knowledge base management
- Semantic search over documentation
- Citation-backed answers
- Multi-document information synthesis

## Performance Metrics

- **Chunk Creation**: ~50-80 chunks from 12 documents
- **Search Time**: <1 second for semantic search
- **Answer Generation**: 2-5 seconds with GPT-4
- **Total Response Time**: <10 seconds end-to-end

## Extensions

### Possible Enhancements
1. **Multi-modal search**: Include product images in search
2. **Conversation history**: Track customer conversation for context
3. **Product recommendations**: Suggest related products based on query
4. **Analytics**: Track most common questions to improve documentation
5. **Fine-tuning**: Train embeddings specifically on outdoor gear domain

### Integration Points
- Shopify/WooCommerce chatbot integration
- Customer service dashboard
- Email autoresponder
- Mobile app Q&A feature

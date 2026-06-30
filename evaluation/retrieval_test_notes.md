# Retrieval Test Notes

## Question 1
Question: What is type 2 diabetes?

Expected source: NHS Diabetes Overview

Actual top source: NHS Diabetes Overview

Result: Good

Notes: The correct definition appeared as Result 1.

## Question 2
Question: What are the symptoms of type 2 diabetes?

Expected source: NHS Type 2 Diabetes Symptoms or NHS Diabetes Overview

Actual top source:

Result: Good

Notes: Returned correct result in one

## Step 3: Evidence Strength Labelling

Evidence strength is now added in `scripts/evidence_label.py` and shown by
`scripts/search_test.py`.

Current labels:

- Strong evidence: retrieved chunks look clearly relevant to the question.
- Partial evidence: some relevant information was found, but support is limited.
- No clear evidence: retrieved chunks are weak, unsupported, out of scope, or the
  question appears unsafe/personal medical.

The current implementation is rule based. It uses:

- the top reranked relevance score
- the average score of the top 3 chunks
- keyword overlap between the question and top chunks
- the number of supporting chunks
- simple unsafe medical question patterns

This should be done before backend and LLM integration because the backend can
return the evidence label as structured data, and the LLM can later be told not
to answer directly when the label is `No clear evidence`.

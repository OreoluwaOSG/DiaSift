# 3.1 Methodology

The method used to develop DiaSift was iterative rather than fixed from the start. The first version of the project was built around a basic retrieval-augmented generation pipeline, then tested with simple Type 2 diabetes questions to see whether the retrieved evidence was actually useful. Some of the early results were too broad or pulled in related but unhelpful material, so the pipeline was adjusted in stages. For that reason, this methodology describes the development process as it happened: collecting and preparing trusted documents, improving retrieval, adding safety checks, and then connecting the pipeline to a backend and user interface.

## 3.1.1 Data Collection and Preparation

The knowledge base was built from public Type 2 diabetes guidance, mainly NHS and NICE material. The current document set includes NHS pages on diabetes overview, Type 2 diabetes treatment, complications, and the NHS Type 2 Diabetes Path to Remission Programme, alongside a NICE overview page for Type 2 diabetes in adults. These sources were selected because they are public, relevant to UK healthcare guidance, and suitable for an educational assistant that needs to ground its responses in recognised information rather than general web content.

The source material was saved as plain text files in the project’s `data/raw` folder. During ingestion, each file is read, cleaned, and converted into smaller chunks. The cleaning step removes empty lines and unnecessary spacing so the text is easier to process. Each chunk is then saved with metadata, including a chunk ID, source name, source file, and chunk index. This metadata is important because DiaSift needs to show where its retrieved evidence came from, rather than returning unsupported answers.

The initial approach to chunking was simpler and closer to a fixed-size split. That was useful for getting the first version working, but it was not ideal for medical guidance. Splitting text too mechanically can separate a point from the explanation around it, or combine sections that are only loosely related. The chunking was therefore revised to use paragraph-based chunks. In the current version, chunks are built up to roughly 900 characters, with one paragraph repeated into the next chunk as overlap. This keeps related guidance together while still making the chunks small enough for retrieval.

## 3.1.2 Retrieval and Embedding Model Selection

The first retrieval tests showed that simply storing the documents in a vector database was not enough. For example, a broad question such as “What is type 2 diabetes?” could return chunks about complications or treatment before returning the basic definition. Those chunks were related to Type 2 diabetes, but they were not the best evidence for answering the question. This made it clear that retrieval quality needed to be checked directly, not assumed.

The project uses `sentence-transformers` to convert both questions and document chunks into embeddings. The current embedding model is `multi-qa-mpnet-base-dot-v1`, which is designed for question-answer retrieval rather than only general sentence similarity. This better matches the way DiaSift is used, because users ask questions while the source documents are written as guidance pages. The ChromaDB collection was also configured to use inner-product scoring, which matches the scoring style expected by this model.

To improve retrieval further, source information is added when creating embeddings. The stored chunk text remains clean, but the embedding model also receives details such as the source name and file name. This gives the model extra context about the document without making the displayed evidence harder to read.

The search step does not rely only on the raw vector score. DiaSift retrieves a wider group of candidate chunks from ChromaDB and then reranks them. The reranking step combines the original semantic ranking with keyword overlap and simple intent-aware rules. For example, if a question is asking for a definition, the system gives more weight to chunks that look like they define the term, while reducing the weight of chunks that are mainly about treatment, complications, or emergency advice. This was added because the raw vector search could identify related material, but not always the most useful passage for the user’s exact question.

## 3.1.3 Safety, Scope and Evidence Handling

Because DiaSift works with health information, the system includes basic safety checks before generating an answer. The aim is not to diagnose users or give personal treatment advice. Instead, the assistant is limited to general educational information from the retrieved sources.

The safety filter is rule based. It looks for questions that appear to ask for personal medical advice, diagnosis, urgent care, medication changes, or dosage decisions. Examples include questions about whether a user should stop medication, whether they personally have diabetes, or what dose they should take. When this type of question is detected, DiaSift returns a safe refusal and advises the user to speak to a qualified healthcare professional. This is a deliberately cautious design choice, as the project is not intended to replace clinical judgement.

A separate scope check is used to decide whether a question belongs within DiaSift’s Type 2 diabetes focus. Questions about diabetes, blood glucose, medication, diet, remission, symptoms, complications, and related lifestyle guidance are treated as in scope. Questions about unrelated topics such as finance, legal issues, or university matters are refused. The scope check also considers retrieved evidence, so a question is not judged only by keywords in the user’s wording.

DiaSift also labels the strength of the retrieved evidence before an answer is produced. The three labels are `Strong evidence`, `Partial evidence`, and `No clear evidence`. These labels are based on signals such as the top reranked score, the average score of the top retrieved chunks, keyword overlap with the question, and the number of supporting chunks. This gives the system a simple way to decide whether it should answer confidently, answer cautiously, or avoid answering because the retrieved material is not clear enough.

## 3.1.4 System Architecture

DiaSift is built as a small web-based RAG system. The backend uses FastAPI and exposes endpoints for checking whether the index is ready and for answering questions. The frontend is built with Next.js and provides a chat-style interface for asking questions and viewing retrieved evidence. ChromaDB is used as the vector store, and `sentence-transformers` is used to generate embeddings.

The backend pipeline follows a fixed order. First, the question is checked for obvious scope issues. Next, unsafe personal medical questions are filtered out before retrieval or LLM generation. If the question is safe and in scope, the system searches the ChromaDB index, reranks the retrieved chunks, labels the evidence strength, and prepares the retrieved passages for answer generation.

LLM generation is optional. By default, the pipeline can run in a dry-run mode, which retrieves evidence and prepares prompts without calling an external model. When enabled, the project supports Gemini as the default provider and also includes OpenAI support. The prompt instructs the model to answer only from the retrieved context, include citations using the source names, avoid diagnosis or personal treatment advice, and state when the provided sources do not contain enough evidence.

This structure separates retrieval, safety checks, evidence labelling, and generation rather than treating the LLM as the whole system. That separation is important for this project because it makes the behaviour easier to inspect. If DiaSift gives a weak answer, it is possible to check whether the issue came from the source material, the retrieval step, the evidence label, or the generated response.

## 3.1.5 Evaluation

The evaluation carried out so far is a small manual and qualitative evaluation rather than a full benchmark. The main focus at this stage was to check whether the system retrieved appropriate evidence for common Type 2 diabetes questions and whether obvious unsafe or unsupported questions were handled cautiously.

Retrieval was tested using simple questions such as “What is type 2 diabetes?” and “What are the complications of type 2 diabetes?”. For each question, the retrieved chunks were inspected to see whether the expected source appeared near the top of the results and whether the text contained enough information to support an answer. This helped identify the earlier retrieval problem where related but less useful chunks, such as complications or treatment sections, could appear above a basic definition. After the chunking, scoring, and reranking changes, the expected overview and complication sources appeared more reliably for these test questions.

The evidence labelling was also checked qualitatively. A useful result should not only be semantically related to the question, but should also contain enough direct support for the answer. This is why the project uses evidence labels rather than treating every retrieved result as equally reliable. The labels are still rule based, so they should be understood as an early support mechanism rather than a clinically validated confidence score.

Safety behaviour was tested by checking whether personal or unsafe medical questions were refused instead of answered directly. The system is designed to avoid giving advice about medication changes, diagnosis, dosage, or urgent symptoms. This does not make the system clinically safe on its own, but it reduces some obvious risks and supports the project’s intended educational scope.

Overall, the evaluation at this stage shows the development progress of the system rather than proving clinical effectiveness. The tests helped guide practical improvements to retrieval and safety handling, but a larger evaluation would still be needed. A stronger final evaluation would use a fixed set of questions, expected sources, relevance judgements, citation checks, and answer-quality scoring.

# document-extraction-engine

1. The Core Problem: The "Data Entry Bottleneck"
In industries like banking, logistics, and insurance, billions of documents (invoices, KYC docs, shipping forms) are processed manually.

The Cost: Human operators are slow and expensive.

The Risk: Manual entry leads to a 1–4% error rate, which can cause massive financial or legal issues.

The AI Flaw: While LLMs are good at reading text, they "hallucinate." A business cannot deploy an AI that might guess a decimal point or a date incorrectly without a way to verify it.

2. Technical Challenges (The "Meat" of your Resume)
To make this a "Senior-level" project, you must address these specific technical hurdles that EigenPal solves:

Unstructured Layouts: Unlike a digital PDF, "messy scans" or handwritten forms don't have underlying text. You have to handle spatial relationships (e.g., "The 'Total' label is next to the number, not above it").

Schema Rigidity: The system must output valid JSON every time. If the AI returns a string where a number is expected, the downstream database breaks.

The Evaluation Cold Start: How do you know the AI is 90% accurate or 99% accurate? Without an automated "Eval" suite, you have to check every result manually, which defeats the purpose of automation.

3. Proposed Project Scope: "The Verified Extraction Pipeline"
Define your project as a pipeline that converts Visual Noise into Verified Data.

Phase A: The Extraction Logic
Input: Multi-page PDFs or JPGs (e.g., 20 different invoice formats).

Processing: Use a Vision-Language Model (VLM) like GPT-4o or Claude 3.5 Sonnet.

Constraint: Use Pydantic to define a strict schema (e.g., invoice_id: int, date: datetime, line_items: List). This ensures the "AI" behaves like a "Software Component."

Phase B: The "Eval-First" Framework (Most Important)
This is what makes it like EigenPal.

Ground Truth: Create a small dataset of 10–20 documents where you have manually typed the correct data into a truth.json file.

The Scorer: Write a Python script that compares the AI's output to your truth.json.

Metrics: Track Levenshtein Distance (for text similarity) and Field-Level Accuracy (did it get the "Total Amount" right 100% of the time?).

4. How to Describe This on a Resume
Instead of saying "I built an AI tool to read invoices," use this:

"Developed an Eval-First Document Extraction Engine that automates structured data recovery from messy scans and handwritten forms. Implemented a Pydantic-based validation layer and an automated evaluation suite to measure extraction accuracy against ground-truth datasets, achieving [X]% accuracy across [Y] different document layouts."

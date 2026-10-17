# Rewind System Design Diagrams

This archive contains the Mermaid source files for the Rewind Fire TV AI companion architecture.

## Contents
1. Use case diagram
2. System context diagram
3. Container architecture
4. Content ingestion pipeline
5. Online question-answering pipeline
6. Ask-question sequence diagram
7. Spoiler-control state diagram
8. Translation pipeline
9. Database ERD
10. Deployment architecture
11. Testing pipeline

## How to view
- Open `.mmd` files in VS Code with a Mermaid extension, or paste the contents into https://mermaid.live.
- Mermaid source is editable text, so you can revise the diagrams for your implementation docs.

## Notes
- These are proposed architecture diagrams, not proof that the system is implemented.
- Fire TV integration with third-party streaming apps is not assumed.
- Safe spoiler filtering must be enforced server-side before LLM context construction.

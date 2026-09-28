from app.retrieval.retriever import retriever


query = "What is the return policy?"

docs = retriever.invoke(query)

print(f"Found {len(docs)} documents\n")

for i, doc in enumerate(docs, 1):

    print(f"--- Document {i} ---")

    print("Source:", doc.metadata.get("source"))
    print("Status:", doc.metadata.get("status"))
    print("Authority:", doc.metadata.get("policy_authority"))
    print("Audience:", doc.metadata.get("audience"))

    print("\nContent:")
    print(doc.page_content)

    print()
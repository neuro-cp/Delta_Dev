def ask_store_prompt(answer: str, confidence: float) -> bool:
    print("\n--- STORE DECISION ---")
    print(answer)
    print(f"confidence: {confidence:.3f}")
    user = input("Store this as memory trace? (y/n): ").strip().lower()
    return user in ["y", "yes"]

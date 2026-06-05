from chat import GeminiChat


def main():
    chat = GeminiChat()
    print("Gemini Chat (輸入 'quit' 離開, 'reset' 清除記憶)\n")

    while True:
        user_input = input("你: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if user_input.lower() == "reset":
            chat.reset()
            print("--- 對話已重置 ---\n")
            continue

        reply = chat.send(user_input)
        print(f"Gemini: {reply}\n")


if __name__ == "__main__":
    main()

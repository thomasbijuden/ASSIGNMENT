import reflex as rx
import httpx

# Replace with your Rasa server URL
RASA_API_URL = "http://localhost:5005/webhooks/rest/webhook"


class State(rx.State):
    messages: list[dict] = [{"role": "assistant", "content": "Hi! I'm your Earphone Store Assistant. How can I help you?"}]
    new_message: str = ""
    is_loading: bool = False

    async def send_to_rasa(self):
        if not self.new_message.strip():
            return
        
        # Add user message
        self.messages.append({"role": "user", "content": self.new_message})
        user_msg = self.new_message
        self.new_message = ""
        self.is_loading = True
        yield
        
        try:
            # Process with Rasa
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    RASA_API_URL,
                    json={"sender": "user", "message": user_msg},
                    headers={"Content-Type": "application/json"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    rasa_data = response.json()
                    for msg in rasa_data:
                        if "text" in msg:
                            self.messages.append({
                                "role": "assistant", 
                                "content": msg["text"]
                            })
                else:
                    self.messages.append({
                        "role": "assistant", 
                        "content": f"Server error: {response.status_code}"
                    })
        
        except Exception as e:
            self.messages.append({
                "role": "assistant", 
                "content": f"Error connecting to server: {str(e)}"
            })

        self.is_loading = False

def message_bubble(message: dict) -> rx.Component:
    return rx.box(
        rx.text(
            message["content"],
            padding="0.75rem 1rem",
            border_radius="8px",
            max_width="80%",
            background = rx.cond(message["role"] == "user", "var(--accent-9)", "var(--accent-3)"),
            # background="var(--accent-9)" if message["role"] == "user" else "var(--accent-3)",
            color= rx.cond(message["role"] == "user", "white", "var(--accent-12)"),
            # color="white" if message["role"] == "user" else "var(--accent-12)",
            align_self= rx.cond(message["role"] == "user", "flex-end", "flex-start"),
            # align_self="flex-end" if message["role"] == "user" else "flex-start",
            text_align=rx.cond(message["role"] == "user", "right", "left" ),
            # text_align="right" if message["role"] == "user" else "left",
            margin_y="0.5rem",
        ),
        width="100%",
        display="flex",
        justify_content=rx.cond(message["role"] == "user", "flex-end", "flex-start"),
        # justify_content="flex-end" if message["role"] == "user" else "flex-start",
    )

def index() -> rx.Component:
    return rx.flex(
        rx.vstack(
            # Header
            rx.heading("🎧 EarZone Chatbot", size="9"),
            rx.divider(margin_bottom="1rem"),
            
            # Chat messages
            rx.auto_scroll(
                rx.foreach(
                    State.messages, 
                    message_bubble
                ),
                height="60vh",
                overflow_y="auto",
                padding="1rem",
                border="1px solid var(--accent-6)",
                border_radius="8px",
                background="var(--accent-1)",
                width="100%",
            ),
            
            # Input area
            rx.form(
                rx.hstack(
                    rx.input(
                        placeholder="Ask about earphones...",
                        value=State.new_message,
                        on_change=State.set_new_message,
                        height="60px",  # Larger input area
                        width="100%",
                        border_radius="6px",
                        border="1px solid var(--accent-7)",
                        padding="0.75rem",
                        _focus={"border": "1px solid var(--accent-9)"},
                        is_disabled=State.is_loading,
                    ),
                    rx.button(
                        rx.cond(
                            State.is_loading,
                            rx.text("Sending..."),
                            "Send"
                        ),
                        type="submit",
                        height="60px",
                        border_radius="6px",
                        padding="0.75rem 1.5rem",
                        background="var(--accent-9)",
                        color="white",
                        _hover={"background": "var(--accent-10)"},
                        is_disabled=State.is_loading,
                    ),
                    width="100%",
                    justify="end",  # Align button to the right
                ),
                on_submit=State.send_to_rasa,
                width="100%",
                margin_top="1rem",
                max_width="800px",
            ),
            width="100%",
            max_width="800px",
        ),
        justify="center",
        padding="2rem",
        height="100vh",
        background="linear-gradient(180deg, var(--accent-1) 0%, var(--accent-2) 100%)",
    )

app = rx.App()
app.add_page(index)
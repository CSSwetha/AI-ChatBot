import streamlit as st
import datetime
import json
import os
from ollama import Client
from PIL import Image
import pytesseract
import io
import base64

# ----------------------------
# Config
# ----------------------------
st.set_page_config(page_title="Chat with Ollama + OCR", page_icon="🤖", layout="wide")
DATA_FILE = "chats.json"

# Initialize Ollama client
try:
    client = Client()
except Exception as e:
    st.error(f"Ollama connection error: {str(e)}")
    client = None

# Configure Tesseract path for Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ----------------------------
# OCR Helper Functions
# ----------------------------
def extract_text_from_image(image, lang='eng'):
    """Extract text from PIL Image using Tesseract OCR"""
    try:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(image, lang=lang, config=custom_config)
        return text.strip()
    except pytesseract.TesseractNotFoundError:
        return "ERROR: Tesseract is not installed or not found. Please install Tesseract OCR."
    except Exception as e:
        return f"Error extracting text: {str(e)}"

def image_to_base64(image):
    """Convert PIL Image to base64 for storage"""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# ----------------------------
# Persistence helpers
# ----------------------------
def load_chats():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
        except IOError as e:
            st.error(f"Error loading chats: {str(e)}")
            return {}
    return {}

def save_chats(chats):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(chats, f, ensure_ascii=False, indent=2, default=str)
    except IOError as e:
        st.error(f"Error saving chats: {str(e)}")

# ----------------------------
# Init session state
# ----------------------------
if "chats" not in st.session_state:
    st.session_state.chats = load_chats()
if "active_chat" not in st.session_state:
    st.session_state.active_chat = None
if "ocr_language" not in st.session_state:
    st.session_state.ocr_language = "eng"
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "llama3.2:1b"
if "show_upload_modal" not in st.session_state:
    st.session_state.show_upload_modal = False

# ----------------------------
# Custom CSS - LIGHT THEME, BLACK TEXT, NO HOVER EFFECTS
# ----------------------------
st.markdown("""
    <style>
    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* App background and main text color */
    .stApp {
        background-color: #ffffff;
        color: #000000 !important;
    }

    /* Main container - light and airy */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 900px;
        background-color: #ffffff !important;
    }

    /* Ensure standard text elements are black for readability */
    html, body, p, div, span, li, .stMarkdown, .stText, .stTextInput, .stExpander {
        color: #000000 !important;
        background-color: transparent !important;
    }

    /* Sidebar - light neutral */
    [data-testid="stSidebar"] {
        background-color: #f8fafc !important; /* very light gray-blue */
        border-right: 1px solid #e6eef6 !important;
    }

    [data-testid="stSidebar"] * {
        color: #000000 !important;
    }

    [data-testid="stSidebar"] h1 {
        color: #0f172a !important;
        font-weight: 700 !important;
        font-size: 1.5rem !important;
        padding: 1rem 0;
    }

    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #0f172a !important;
        font-weight: 600 !important;
    }

    /* Chat messages - subtle borders, white background */
    .chat-message {
        padding: 1rem;
        margin: 0.75rem 0;
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        font-size: 1rem;
        line-height: 1.5;
        border: 1px solid #e6eef6;
        background-color: #ffffff !important;
        color: #000000 !important;
    }

    .user-message {
        background-color: #eef2ff !important; /* pale blue */
        border-color: #dbeafe !important;
        color: #000000 !important;
    }

    .user-message * {
        color: #000000 !important;
    }

    .assistant-message {
        background-color: #f3f4f6 !important; /* light gray */
        border-color: #e5e7eb !important;
        color: #000000 !important;
    }

    .assistant-message * {
        color: #000000 !important;
    }

    /* OCR Results - readable monospace on light background */
    .ocr-container {
        background-color: #ffffff !important;
        border: 1px solid #f1c27d !important;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 6px;
        font-family: 'Courier New', monospace;
        font-size: 0.95rem;
        color: #000000 !important;
    }

    .ocr-title {
        font-weight: 700;
        color: #92400e !important;
        margin-bottom: 0.5rem;
        font-size: 1rem;
    }

    .ocr-container pre {
        color: #000000 !important;
        background-color: transparent !important;
        border: none !important;
        margin: 0 !important;
        padding: 0.5rem 0 !important;
    }

    /* Image preview in chat */
    .image-preview {
        max-width: 400px;
        border-radius: 8px;
        margin: 0.5rem 0;
        border: 1px solid #e5e7eb;
        background-color: #ffffff;
    }

    /* Buttons - flat, no hover changes */
    .stButton button {
        border-radius: 8px;
        font-weight: 600;
        transition: none !important;
        border: 1px solid #cbd5e1 !important;
        background-color: #f1f5f9 !important; /* very light gray */
        color: #000000 !important;
    }

    /* Keep sidebar buttons consistent - no hovering transform */
    [data-testid="stSidebar"] .stButton button {
        background-color: #f1f5f9 !important;
        color: #000000 !important;
        border: 1px solid #e6eef6 !important;
        font-size: 0.95rem;
        font-weight: 600;
    }

    /* Remove hover pseudo-class effects by ensuring :hover equals base */
    .stButton button:hover,
    [data-testid="stSidebar"] .stButton button:hover,
    [data-testid="stSidebar"] button[kind="primary"]:hover,
    [data-testid="stSidebar"] .streamlit-expanderHeader:hover {
        background-color: inherit !important;
        color: inherit !important;
        border-color: inherit !important;
        transform: none !important;
        box-shadow: none !important;
    }

    /* Selectbox styling */
    [data-testid="stSidebar"] .stSelectbox label {
        color: #0f172a !important;
        font-weight: 600;
        font-size: 1rem;
    }

    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {
        background-color: #ffffff !important;
        border: 1px solid #e6eef6 !important;
    }

    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {
        color: #000000 !important;
    }

    /* Expander styling - no hover visual changes */
    [data-testid="stSidebar"] .streamlit-expanderHeader {
        background-color: #ffffff !important;
        color: #0f172a !important;
        font-weight: 600;
        border-radius: 6px;
        border: 1px solid #e6eef6 !important;
    }

    /* File uploader styling */
    .uploadedFile {
        background-color: #ffffff !important;
        border: 1px solid #e6eef6 !important;
        color: #000000 !important;
    }

    [data-testid="stFileUploader"] {
        background-color: #ffffff !important;
        border: 1px solid #e6eef6 !important;
        border-radius: 8px;
        padding: 1rem;
    }

    [data-testid="stFileUploader"] label {
        color: #0f172a !important;
        font-weight: 600;
    }

    [data-testid="stFileUploader"] * {
        color: #000000 !important;
    }

    /* Chat input styling */
    .stChatInput > div {
        border: 1px solid #e6eef6 !important;
        background-color: #ffffff !important;
        border-radius: 8px;
    }

    .stChatInput input {
        color: #000000 !important;
        background-color: #ffffff !important;
    }

    .stChatInput input::placeholder {
        color: #6b7280 !important;
    }

    /* Welcome screen */
    .welcome-container {
        background-color: transparent !important;
        text-align: center;
        padding: 3rem;
    }

    .welcome-container h1 {
        color: #0f172a !important;
        font-weight: 700;
        margin-bottom: 1rem;
    }

    .welcome-container h3 {
        color: #1f2937 !important;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }

    .welcome-container p {
        color: #374151 !important;
        font-size: 1.1rem;
    }

    /* Spinner color */
    .stSpinner > div {
        border-top-color: #0f172a !important;
    }

    /* Success/Error messages - lighter appearance */
    .stSuccess {
        background-color: #ecfdf5 !important;
        color: #064e3b !important;
        border: 1px solid #bbf7d0 !important;
    }

    .stError {
        background-color: #fff1f2 !important;
        color: #7f1d1d !important;
        border: 1px solid #fecaca !important;
    }

    /* Image in messages */
    .stImage {
        border-radius: 8px;
        border: 1px solid #e6eef6;
    }

    /* Horizontal rule */
    hr {
        border-color: #e6eef6 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------
# Sidebar
# ----------------------------
with st.sidebar:
    st.title("💬 AI Vision Chat")
    
    # New chat button
    if st.button("➕ New Chat", type="primary", use_container_width=True):
        cid = str(datetime.datetime.now().timestamp())
        st.session_state.chats[cid] = {
            "title": "New Chat",
            "messages": [],
            "created": str(datetime.datetime.now())
        }
        st.session_state.active_chat = cid
        save_chats(st.session_state.chats)
        st.rerun()
    
    st.markdown("---")
    
    # Model Settings
    with st.expander("⚙️ Settings", expanded=False):
        available_models = [
            "llama3.2:1b",
            "llama3.2:3b",
            "llama3:8b",
            "phi3:mini",
        ]
        
        st.session_state.selected_model = st.selectbox(
            "Model",
            available_models,
            index=0,
        )
        
        st.session_state.ocr_language = st.selectbox(
            "OCR Language",
            ["eng", "spa", "fra", "deu", "chi_sim", "jpn", "hin"],
            index=0,
        )
    
    st.markdown("---")
    st.subheader("Recent Chats")
    
    # Chat history
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    groups = {"Today": [], "Yesterday": [], "Older": []}

    for cid, chat in st.session_state.chats.items():
        created_str = chat.get("created")
        if created_str:
            try:
                created_date = datetime.date.fromisoformat(created_str.split(" ")[0])
                if created_date == today:
                    groups["Today"].append((cid, chat))
                elif created_date == yesterday:
                    groups["Yesterday"].append((cid, chat))
                else:
                    groups["Older"].append((cid, chat))
            except (ValueError, IndexError):
                groups["Older"].append((cid, chat))
        else:
            groups["Older"].append((cid, chat))

    for label, chats in groups.items():
        if chats:
            st.markdown(f"**{label}**")
            for cid, chat in chats:
                cols = st.columns([4, 1])
                with cols[0]:
                    if st.button(chat["title"][:30], key=f"open_{cid}", use_container_width=True):
                        st.session_state.active_chat = cid
                        st.rerun()
                with cols[1]:
                    if st.button("🗑", key=f"del_{cid}"):
                        del st.session_state.chats[cid]
                        save_chats(st.session_state.chats)
                        if st.session_state.active_chat == cid:
                            st.session_state.active_chat = None
                        st.rerun()

# ----------------------------
# Main Chat Area
# ----------------------------
if st.session_state.active_chat is None:
    st.markdown("""
        <div class='welcome-container'>
            <h1>🤖 AI Vision Chat</h1>
            <h3>Upload images and ask questions!</h3>
            <p>I can read text from images and answer your questions about them</p>
        </div>
    """, unsafe_allow_html=True)
else:
    chat = st.session_state.chats[st.session_state.active_chat]
    
    # Display chat messages
    for msg in chat["messages"]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # Create message container
        msg_class = "user-message" if role == "user" else "assistant-message"
        
        st.markdown(f"<div class='chat-message {msg_class}'>", unsafe_allow_html=True)
        
        # Show image if present
        if msg.get("image_data"):
            try:
                img_bytes = base64.b64decode(msg["image_data"])
                st.image(img_bytes, width=300, caption="📷 Uploaded Image")
            except Exception as e:
                st.error(f"Error displaying image: {str(e)}")
        
        # Show OCR result if present
        if msg.get("ocr_text"):
            st.markdown(
                f"""<div class='ocr-container'>
                    <div class='ocr-title'>📄 Extracted Text:</div>
                    <pre>{msg['ocr_text']}</pre>
                </div>""",
                unsafe_allow_html=True
            )
        
        # Show message content
        if content:
            # Ensure displayed text uses black color on light background
            st.markdown(f"<div style='color: #000000'>{content}</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Spacer for fixed input
    st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)

# ----------------------------
# Image Upload Modal
# ----------------------------
if st.session_state.show_upload_modal and st.session_state.active_chat:
    st.markdown("### 📤 Upload Image")
    
    uploaded_file = st.file_uploader(
        "Choose an image",
        type=["png", "jpg", "jpeg", "bmp", "tiff"],
        key="image_uploader"
    )
    
    if uploaded_file:
        try:
            image = Image.open(uploaded_file)
            st.image(image, caption="Preview", use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔍 Extract Text", use_container_width=True):
                    with st.spinner("Extracting text..."):
                        ocr_text = extract_text_from_image(image, st.session_state.ocr_language)
                        
                        if ocr_text and not ocr_text.startswith("ERROR"):
                            img_base64 = image_to_base64(image)
                            chat = st.session_state.chats[st.session_state.active_chat]
                            chat["messages"].append({
                                "role": "user",
                                "content": "📷 Image uploaded",
                                "image_data": img_base64,
                                "ocr_text": ocr_text
                            })
                            save_chats(st.session_state.chats)
                            st.session_state.show_upload_modal = False
                            st.success("✅ Text extracted successfully!")
                            st.rerun()
                        else:
                            st.error(ocr_text)
            
            with col2:
                if st.button("🤖 Analyze", use_container_width=True):
                    if client:
                        with st.spinner("Analyzing image..."):
                            ocr_text = extract_text_from_image(image, st.session_state.ocr_language)
                            
                            if ocr_text and not ocr_text.startswith("ERROR"):
                                img_base64 = image_to_base64(image)
                                chat = st.session_state.chats[st.session_state.active_chat]
                                
                                # Add image to chat
                                chat["messages"].append({
                                    "role": "user",
                                    "content": "📷 Please analyze this image",
                                    "image_data": img_base64,
                                    "ocr_text": ocr_text
                                })
                                
                                # Simple, direct analysis
                                api_messages = [{
                                    "role": "user",
                                    "content": f"Here is text extracted from an image. Please analyze it and tell me what it's about:\n\n{ocr_text}"
                                }]
                                
                                try:
                                    response_text = ""
                                    for chunk in client.chat(
                                        model=st.session_state.selected_model,
                                        messages=api_messages,
                                        stream=True
                                    ):
                                        if "message" in chunk and "content" in chunk["message"]:
                                            response_text += chunk["message"]["content"]
                                    
                                    chat["messages"].append({
                                        "role": "assistant",
                                        "content": response_text
                                    })
                                    save_chats(st.session_state.chats)
                                    st.session_state.show_upload_modal = False
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Analysis error: {str(e)}")
                            else:
                                st.error("Could not extract text from image")
                    else:
                        st.error("Ollama not connected")
            
            with col3:
                if st.button("💾 Save", use_container_width=True):
                    img_base64 = image_to_base64(image)
                    ocr_text = extract_text_from_image(image, st.session_state.ocr_language)
                    chat = st.session_state.chats[st.session_state.active_chat]
                    chat["messages"].append({
                        "role": "user",
                        "content": "💾 Image saved",
                        "image_data": img_base64,
                        "ocr_text": ocr_text if not ocr_text.startswith("ERROR") else None
                    })
                    save_chats(st.session_state.chats)
                    st.session_state.show_upload_modal = False
                    st.success("✅ Image saved!")
                    st.rerun()
        
        except Exception as e:
            st.error(f"Error processing image: {str(e)}")
    
    if st.button("✖ Close", use_container_width=True):
        st.session_state.show_upload_modal = False
        st.rerun()

# ----------------------------
# Chat Input with Upload Button
# ----------------------------
if st.session_state.active_chat:
    # Create columns for upload button and input
    col1, col2 = st.columns([1, 20])
    
    with col1:
        if st.button("📎", key="upload_trigger", help="Upload Image"):
            st.session_state.show_upload_modal = True
            st.rerun()
    
    with col2:
        user_input = st.chat_input("Ask anything about the images...")
        
        if user_input:
            chat = st.session_state.chats[st.session_state.active_chat]
            
            # Add user message
            chat["messages"].append({"role": "user", "content": user_input})
            
            if chat["title"] == "New Chat":
                chat["title"] = user_input[:30] + ("..." if len(user_input) > 30 else "")
            
            save_chats(st.session_state.chats)
            
            if client:
                with st.spinner("Thinking..."):
                    try:
                        # Build conversation with full context
                        api_messages = []
                        
                        # Collect all OCR text from images
                        image_data = []
                        for idx, m in enumerate(chat["messages"]):
                            if m.get("ocr_text"):
                                image_data.append({
                                    "index": len(image_data) + 1,
                                    "content": m["ocr_text"]
                                })
                        
                        # If there are images, add them as context in the conversation
                        if image_data:
                            # Create a context message with all image content
                            context_parts = []
                            for img in image_data:
                                context_parts.append(f"IMAGE {img['index']}:\n{img['content']}")
                            
                            full_image_context = "\n\n---\n\n".join(context_parts)
                            
                            # Add system-like context as a user message (works better with some models)
                            api_messages.append({
                                "role": "user",
                                "content": f"I have uploaded {len(image_data)} image(s) with the following content:\n\n{full_image_context}"
                            })
                            
                            api_messages.append({
                                "role": "assistant",
                                "content": "I understand. I have processed the image content you provided. I will use this information to answer your questions accurately."
                            })
                        
                        # Add recent conversation (last 10 messages, excluding image upload notifications)
                        recent_msgs = []
                        for m in chat["messages"][-11:-1]:  # Exclude the current message
                            if m.get("content") and not m["content"].startswith(("📷", "💾")):
                                recent_msgs.append(m)
                        
                        # Add the filtered conversation
                        for m in recent_msgs:
                            api_messages.append({
                                "role": m["role"],
                                "content": m["content"]
                            })
                        
                        # Add the current user question
                        api_messages.append({
                            "role": "user",
                            "content": user_input
                        })
                        
                        # Get response from model
                        response_text = ""
                        for chunk in client.chat(
                            model=st.session_state.selected_model,
                            messages=api_messages,
                            stream=True
                        ):
                            if "message" in chunk and "content" in chunk["message"]:
                                response_text += chunk["message"]["content"]
                        
                        chat["messages"].append({"role": "assistant", "content": response_text})
                        save_chats(st.session_state.chats)
                        st.rerun()
                    
                    except Exception as e:
                        error_msg = str(e)
                        if "memory" in error_msg.lower() or "500" in error_msg:
                            error_response = "⚠️ Memory error! Try switching to llama3.2:1b in Settings or start a new chat."
                        else:
                            error_response = f"⚠️ Error: {error_msg}"
                        
                        chat["messages"].append({"role": "assistant", "content": error_response})
                        save_chats(st.session_state.chats)
                        st.rerun()
            else:
                st.error("Ollama is not connected. Please start Ollama first.")

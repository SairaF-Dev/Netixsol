import requests, streamlit as st

st.set_page_config(page_title="AFL Assistant", page_icon="🏉")
st.title("🏉 AFL Assistant")
st.caption("Domain-locked AFL chat + prediction assistant")

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id="streamlit-demo"

if "messages" not in st.session_state:
    st.session_state.messages=[]

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

q=st.chat_input("Ask an AFL question...")
if q:
    st.session_state.messages.append({"role":"user","content":q})
    with st.chat_message("user"):
        st.markdown(q)
    try:
        r=requests.post(
            "http://127.0.0.1:8000/chat",
            json={"message":q,"conversation_id":st.session_state.conversation_id},
            timeout=30,
        )
        data=r.json()
        answer=data.get("response","")
    except Exception as exc:
        answer=f"API connection error: {exc}"
    st.session_state.messages.append({"role":"assistant","content":answer})
    with st.chat_message("assistant"):
        st.markdown(answer)

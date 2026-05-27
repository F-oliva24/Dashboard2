"""
auth.py — Autenticazione admin/guest.
"""
import json
import secrets
import string
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
from config import GUEST_PW_FILE, GUEST_HOURS, C


def gen_guest_pw(n=10) -> str:
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(n))


def get_admin_pw() -> str:
    try:
        return st.secrets["ADMIN_PASSWORD"]
    except:
        return "admin123"


def save_guest_pw(password: str, expiry: datetime) -> None:
    with open(GUEST_PW_FILE, "w") as f:
        json.dump({"password": password, "expiry": expiry.isoformat()}, f)


def load_guest_pw() -> tuple:
    if not GUEST_PW_FILE.exists():
        return None, None
    try:
        with open(GUEST_PW_FILE) as f:
            data = json.load(f)
        pw  = data.get("password")
        exp = datetime.fromisoformat(data["expiry"]) if "expiry" in data else None
        return pw, exp
    except:
        return None, None


def check_auth() -> str | None:
    if "auth_role" not in st.session_state:
        return None
    if st.session_state["auth_role"] == "guest":
        _, exp = load_guest_pw()
        if exp and datetime.now() > exp:
            st.session_state.pop("auth_role", None)
            return None
    return st.session_state["auth_role"]


def render_login() -> None:
    st.markdown(f"""
    <div style="max-width:420px;margin:80px auto;background:{C['card']};
                border:1px solid {C['border']};border-radius:16px;padding:40px;text-align:center">
      <div style="font-size:28px;font-weight:800;margin-bottom:8px">📈 Investment Dashboard</div>
      <div style="color:{C['muted']};font-size:13px;margin-bottom:28px">Enter your password to continue</div>
    </div>
    """, unsafe_allow_html=True)
    col = st.columns([1, 2, 1])[1]
    with col:
        pw = st.text_input("Password", type="password", placeholder="Enter password...")
        if st.button("Access Dashboard", type="primary", use_container_width=True):
            guest_pw, guest_exp = load_guest_pw()
            if pw == get_admin_pw():
                st.session_state["auth_role"] = "admin"
                st.rerun()
            elif guest_pw and pw == guest_pw and guest_exp and datetime.now() < guest_exp:
                st.session_state["auth_role"] = "guest"
                st.rerun()
            else:
                st.error("Wrong password or expired guest access.")


def render_auth_sidebar(is_admin: bool) -> None:
    if is_admin:
        st.sidebar.markdown('<span class="badge-admin">⚡ Admin</span>', unsafe_allow_html=True)
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Guest Access**")
        if st.sidebar.button("🔑 Generate Guest Password"):
            pw  = gen_guest_pw()
            exp = datetime.now() + timedelta(hours=GUEST_HOURS)
            save_guest_pw(pw, exp)
            st.sidebar.success(f"Password: `{pw}`")
            st.sidebar.caption(f"Expires at {exp.strftime('%H:%M')} ({GUEST_HOURS}h)")
        guest_pw, guest_exp = load_guest_pw()
        if guest_pw and guest_exp and datetime.now() < guest_exp:
            rem = int((guest_exp - datetime.now()).seconds / 60)
            st.sidebar.info(f"Active: `{guest_pw}` — {rem} min left")
        elif guest_pw:
            st.sidebar.caption("Guest password expired.")
    else:
        st.sidebar.markdown('<span class="badge-guest">👁 Guest (read-only)</span>', unsafe_allow_html=True)
        exp = load_guest_pw()[1]
        if exp:
            rem = max(0, int((exp - datetime.now()).seconds / 60))
            st.sidebar.caption(f"Session expires in {rem} min")
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.pop("auth_role", None)
        st.rerun()

"""
视频工厂 v4 - 修复版
修复: 自动流转 + 删除空壳功能 + 加文字模式 + 加引导
"""

import os
import sys
import json
import time
import tempfile
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.copywriter import generate_all_copy
from core.voice_clone import voice_clone, FISH_API_KEY, FISH_VOICES
from core.pipeline import process_video, process_text_to_video
from core.templates import list_templates
from core.history import get_history, delete_history
from core.asr import transcribe

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(BASE_DIR, "output"), exist_ok=True)

st.set_page_config(page_title="AI 视频工厂", page_icon="🎬", layout="centered")

# ===== 样式 =====
st.markdown("""
<style>
    .stApp { background: #1a1a2e; }
    h1, h2, h3, h4 { color: #fff !important; }
    .step-card {
        background: #16213e; border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px; padding: 1.5rem; margin-bottom: 1rem;
    }
    .step-num {
        display: inline-block; background: #667eea; color: white;
        width: 28px; height: 28px; border-radius: 50%; text-align: center;
        line-height: 28px; font-weight: 700; font-size: 0.9rem; margin-right: 0.5rem;
    }
    .step-title { color: #fff; font-size: 1.1rem; font-weight: 700; display: inline; }
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important; font-weight: 700 !important;
        border-radius: 10px !important; border: none !important;
        padding: 0.6rem 1.5rem !important;
    }
    .stButton > button:hover { box-shadow: 0 4px 15px rgba(102,126,234,0.4); }
    .stDownloadButton > button {
        background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%) !important;
        color: white !important; font-weight: 700 !important; border-radius: 10px !important;
    }
    .stTextArea textarea, .stTextInput input {
        background: rgba(255,255,255,0.05) !important; color: #fff !important;
        border: 1px solid rgba(255,255,255,0.15) !important; border-radius: 10px !important;
    }
    .stProgress > div > div > div > div { background: linear-gradient(90deg, #667eea, #764ba2) !important; }
    .guide-box {
        background: rgba(102,126,234,0.1); border: 1px solid rgba(102,126,234,0.3);
        border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ===== 标题 =====
st.markdown("<h1 style='text-align:center;'>🎬 AI 视频工厂</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#888;margin-top:-0.5rem;'>上传素材，AI 自动出片</p>", unsafe_allow_html=True)

# ===== 模式选择 =====
mode = st.radio(
    "选择模式",
    ["📹 上传视频自动剪辑", "📝 输入文字生成视频"],
    horizontal=True,
    label_visibility="collapsed",
)

# ===== 模式 1：上传视频 =====
if mode == "📹 上传视频自动剪辑":
    st.markdown("""
    <div class="guide-box">
        <b>使用说明：</b>上传视频 → 选择模板 → 点击一键出片 → 等待处理 → 下载成品
    </div>
    """, unsafe_allow_html=True)

    # 选模板
    st.markdown("### 📌 选择模板")
    templates = list_templates()
    cols = st.columns(4)
    selected = st.session_state.get("template", "douyin")
    for i, tmpl in enumerate(templates):
        with cols[i]:
            if st.button(f"{tmpl['name']}", key=f"t_{tmpl['id']}", use_container_width=True):
                st.session_state["template"] = tmpl["id"]
                st.rerun()
    st.caption(f"当前：{get_template_name(selected, templates)}")

    # 上传视频
    st.markdown("### 📁 上传视频")
    uploaded = st.file_uploader(
        "选择视频文件",
        type=["mp4", "mov", "avi", "mkv", "webm"],
        label_visibility="collapsed",
        key="main_upload",
    )

    if uploaded:
        st.video(uploaded)

        # 一键出片
        if st.button("🚀 一键出片", use_container_width=True, type="primary", key="go"):
            tmp_dir = tempfile.mkdtemp()
            input_path = os.path.join(tmp_dir, uploaded.name)
            with open(input_path, "wb") as f:
                f.write(uploaded.read())

            output_dir = os.path.join(BASE_DIR, "output")
            progress = st.progress(0)
            status = st.empty()

            def update(pct, msg):
                progress.progress(pct)
                status.markdown(f"<span style='color:#667eea;'>{msg}</span>", unsafe_allow_html=True)

            result = process_video(input_path, st.session_state.get("template", "douyin"), output_dir, progress_callback=update)

            if "error" in result:
                st.error(f"失败: {result['error']}")
            else:
                progress.progress(100)
                status.markdown("<span style='color:#38ef7d;'>✅ 完成!</span>", unsafe_allow_html=True)

                # 显示结果
                col_v, col_d = st.columns([3, 2])
                with col_v:
                    st.video(result["output_path"])
                with col_d:
                    if result.get("title"):
                        st.markdown(f"**📌 {result['title']}**")
                    if result.get("copy"):
                        with st.expander("📝 AI 文案"):
                            st.text(result["copy"])
                    with open(result["output_path"], "rb") as f:
                        st.download_button("⬇️ 下载视频", f.read(),
                                           file_name="video.mp4", mime="video/mp4",
                                           use_container_width=True)
                    if result.get("cover_path") and os.path.exists(result["cover_path"]):
                        with open(result["cover_path"], "rb") as f:
                            st.download_button("🖼️ 下载封面", f.read(),
                                               file_name="cover.jpg", mime="image/jpeg",
                                               use_container_width=True)
    else:
        st.info("👆 上传视频后点击「一键出片」")

# ===== 模式 2：文字生成 =====
else:
    st.markdown("""
    <div class="guide-box">
        <b>使用说明：</b>输入你想说的内容 → 选择模板 → AI 自动生成配音+字幕+视频
    </div>
    """, unsafe_allow_html=True)

    # 选模板
    st.markdown("### 📌 选择模板")
    templates = list_templates()
    cols = st.columns(4)
    selected = st.session_state.get("template_text", "douyin")
    for i, tmpl in enumerate(templates):
        with cols[i]:
            if st.button(f"{tmpl['name']}", key=f"tt_{tmpl['id']}", use_container_width=True):
                st.session_state["template_text"] = tmpl["id"]
                st.rerun()
    st.caption(f"当前：{get_template_name(selected, templates)}")

    # 输入文字
    st.markdown("### ✍️ 输入内容")
    text = st.text_area(
        "你想说什么",
        placeholder="今天教大家一个方法，可以让你的工作效率提高3倍...",
        height=180,
        label_visibility="collapsed",
        key="text_input",
    )

    if text.strip():
        st.caption(f"已输入 {len(text)} 字，预计 {len(text)//5} 秒语音")

        if st.button("🚀 一键生成", use_container_width=True, type="primary", key="go_text"):
            output_dir = os.path.join(BASE_DIR, "output")
            progress = st.progress(0)
            status = st.empty()

            def update(pct, msg):
                progress.progress(pct)
                status.markdown(f"<span style='color:#667eea;'>{msg}</span>", unsafe_allow_html=True)

            result = process_text_to_video(text, st.session_state.get("template_text", "douyin"), output_dir, progress_callback=update)

            if "error" in result:
                st.error(f"失败: {result['error']}")
            else:
                progress.progress(100)
                status.markdown("<span style='color:#38ef7d;'>✅ 完成!</span>", unsafe_allow_html=True)

                col_v, col_d = st.columns([3, 2])
                with col_v:
                    st.video(result["output_path"])
                with col_d:
                    if result.get("title"):
                        st.markdown(f"**📌 {result['title']}**")
                    if result.get("copy"):
                        with st.expander("📝 AI 文案"):
                            st.text(result["copy"])
                    with open(result["output_path"], "rb") as f:
                        st.download_button("⬇️ 下载视频", f.read(),
                                           file_name="text_video.mp4", mime="video/mp4",
                                           use_container_width=True)
                    if result.get("cover_path") and os.path.exists(result["cover_path"]):
                        with open(result["cover_path"], "rb") as f:
                            st.download_button("🖼️ 下载封面", f.read(),
                                               file_name="cover.jpg", mime="image/jpeg",
                                               use_container_width=True)
    else:
        st.info("👆 输入文字后点击「一键生成」")

# ===== 历史记录 =====
st.markdown("---")
st.markdown("### 📋 历史记录")

history = get_history(5)
if history:
    for h in history:
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{h.get('title', '未命名')}**")
                st.caption(f"{h.get('time_str', '')} | {h.get('elapsed', 0):.0f}s")
            with col2:
                if h.get("output_path") and os.path.exists(h["output_path"]):
                    with open(h["output_path"], "rb") as f:
                        st.download_button("⬇️ 下载", f.read(),
                                           file_name=f"{h.get('task_id', 'v')}.mp4",
                                           mime="video/mp4", key=f"dl_{h.get('task_id')}")
else:
    st.info("暂无历史记录")


# ===== 工具函数 =====
def get_template_name(template_id: str, templates: list) -> str:
    for t in templates:
        if t["id"] == template_id:
            return f"{t['name']} - {t['desc']}"
    return "抖音热门"

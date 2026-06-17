"""
视频工厂 v4 - 完善版
保留 5 步流程，每个步骤功能完善
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
        border-radius: 12px; padding: 1rem; margin-bottom: 1rem; font-size: 0.85rem;
    }
    .tag { display:inline-block; padding:2px 8px; border-radius:6px; font-size:0.75rem; margin:0.1rem; }
    .tag-active { background:#667eea; color:white; }
    .tag-inactive { background:rgba(255,255,255,0.1); color:#888; }
</style>
""", unsafe_allow_html=True)

# ===== 标题 =====
st.markdown("<h1 style='text-align:center;'>🎬 AI 视频工厂</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#888;margin-top:-0.5rem;'>5 步自动出片，从文案到发布</p>", unsafe_allow_html=True)

# ===== 初始化 session =====
for key in ["step", "extracted_copy", "rewritten_copy", "title", "cover_text", "template",
            "audio_path", "uploaded_video_path", "voice_style"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key != "step" else 1
if not st.session_state.template:
    st.session_state.template = "douyin"

# ===== 模式选择 =====
mode = st.radio(
    "选择模式",
    ["📹 上传视频", "📝 输入文字"],
    horizontal=True,
    label_visibility="collapsed",
)

# ==================== 模式 1：上传视频 ====================
if mode == "📹 上传视频":

    st.markdown("""
    <div class="guide-box">
        💡 <b>使用流程：</b>上传视频 → AI 自动提取文案 → 选择模板仿写 → 生成语音 → 一键出片
    </div>
    """, unsafe_allow_html=True)

    # ===== 步骤 1：获取文案 =====
    st.markdown("""
    <div class="step-card">
        <span class="step-num">1</span>
        <span class="step-title">上传视频，提取文案</span>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "上传视频文件",
        type=["mp4", "mov", "avi", "mkv", "webm"],
        label_visibility="collapsed",
        key="step1_upload",
    )

    if uploaded:
        st.video(uploaded)

        if st.button("⚡ 提取文案", key="extract_btn"):
            tmp = tempfile.mkdtemp()
            path = os.path.join(tmp, uploaded.name)
            with open(path, "wb") as f:
                f.write(uploaded.read())
            with st.spinner("正在识别语音..."):
                segments = transcribe(path, model_size="base")
                full_text = " ".join([s["text"] for s in segments])
                st.session_state.extracted_copy = full_text
                st.session_state.uploaded_video_path = path
            st.success("文案提取完成!")

    if st.session_state.extracted_copy:
        st.text_area("提取的文案", st.session_state.extracted_copy, height=120, key="show_extract", disabled=True)

    # ===== 步骤 2：选择模板 + 仿写 =====
    st.markdown("""
    <div class="step-card">
        <span class="step-num">2</span>
        <span class="step-title">选择模板，AI 仿写文案</span>
    </div>
    """, unsafe_allow_html=True)

    templates = list_templates()
    cols = st.columns(4)
    for i, tmpl in enumerate(templates):
        with cols[i]:
            if st.button(f"{tmpl['name']}", key=f"t_{tmpl['id']}", use_container_width=True):
                st.session_state.template = tmpl["id"]
                st.rerun()
    st.caption(f"当前模板：{get_template_name(st.session_state.template, templates)}")

    if st.button("📝 AI 仿写文案", key="rewrite_btn"):
        text_to_rewrite = st.session_state.extracted_copy or ""
        if text_to_rewrite.strip():
            with st.spinner("AI 正在仿写..."):
                result = generate_all_copy(text_to_rewrite, st.session_state.template)
                st.session_state.rewritten_copy = result["copy"]
                st.session_state.title = result["title"]
                st.session_state.cover_text = result
            st.success("仿写完成!")
        else:
            st.warning("请先在第 1 步上传视频提取文案")

    if st.session_state.rewritten_copy:
        st.text_area("仿写结果", st.session_state.rewritten_copy, height=150, key="show_rewrite", disabled=True)
        if st.session_state.title:
            st.markdown(f"**📌 标题：** {st.session_state.title}")

    # ===== 步骤 3：声音克隆 =====
    st.markdown("""
    <div class="step-card">
        <span class="step-num">3</span>
        <span class="step-title">选择声音，生成配音</span>
    </div>
    """, unsafe_allow_html=True)

    voice_options = list(FISH_VOICES.keys()) if FISH_API_KEY else ["温柔女声", "新闻播报", "活泼女声", "沉稳男声"]
    selected_voice = st.selectbox("选择声音风格", voice_options, key="voice_select")

    if st.button("🔊 生成语音", key="gen_voice"):
        text = st.session_state.rewritten_copy or ""
        if text.strip():
            with st.spinner("正在合成语音..."):
                tmp_dir = tempfile.mkdtemp()
                audio_path = os.path.join(tmp_dir, "voice.mp3")
                voice_clone(text, voice_style=selected_voice, output_path=audio_path)
                st.session_state.audio_path = audio_path
                st.session_state.voice_style = selected_voice
            st.success("语音生成完成!")
        else:
            st.warning("请先仿写文案")

    if st.session_state.get("audio_path") and os.path.exists(st.session_state.audio_path):
        st.audio(st.session_state.audio_path)

    # ===== 步骤 4：一键出片 =====
    st.markdown("""
    <div class="step-card">
        <span class="step-num">4</span>
        <span class="step-title">一键出片</span>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 一键出片", use_container_width=True, type="primary", key="full_pipeline"):
            if st.session_state.uploaded_video_path:
                output_dir = os.path.join(BASE_DIR, "output")
                progress = st.progress(0)
                status = st.empty()

                def update(pct, msg):
                    progress.progress(pct)
                    status.markdown(f"<span style='color:#667eea;'>{msg}</span>", unsafe_allow_html=True)

                result = process_video(st.session_state.uploaded_video_path, st.session_state.template, output_dir, progress_callback=update)

                if "error" in result:
                    st.error(f"失败: {result['error']}")
                else:
                    progress.progress(100)
                    status.markdown("<span style='color:#38ef7d;'>✅ 完成!</span>", unsafe_allow_html=True)

                    st.session_state.result = result
                    st.rerun()
            else:
                st.warning("请先在第 1 步上传视频")

    with col2:
        if st.button("🔄 重新生成", use_container_width=True, key="regen"):
            st.session_state.rewritten_copy = ""
            st.session_state.title = ""
            st.session_state.extracted_copy = ""
            st.session_state.result = None
            st.rerun()

    # 显示结果
    if st.session_state.get("result"):
        result = st.session_state.result
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
                st.download_button("⬇️ 下载视频", f.read(), file_name="video.mp4", mime="video/mp4", use_container_width=True)
            if result.get("cover_path") and os.path.exists(result["cover_path"]):
                with open(result["cover_path"], "rb") as f:
                    st.download_button("🖼️ 下载封面", f.read(), file_name="cover.jpg", mime="image/jpeg", use_container_width=True)
            if result.get("srt_path") and os.path.exists(result["srt_path"]):
                with open(result["srt_path"], "r", encoding="utf-8") as f:
                    st.download_button("📄 下载字幕", f.read(), file_name="subtitles.srt", use_container_width=True)

# ==================== 模式 2：输入文字 ====================
else:

    st.markdown("""
    <div class="guide-box">
        💡 <b>使用流程：</b>输入文字 → 选择模板 → AI 自动生成配音+字幕+视频
    </div>
    """, unsafe_allow_html=True)

    # 选模板
    st.markdown("### 📌 选择模板")
    templates = list_templates()
    cols = st.columns(4)
    for i, tmpl in enumerate(templates):
        with cols[i]:
            if st.button(f"{tmpl['name']}", key=f"tt_{tmpl['id']}", use_container_width=True):
                st.session_state["template_text"] = tmpl["id"]
                st.rerun()
    st.caption(f"当前模板：{get_template_name(st.session_state.get('template_text', 'douyin'), templates)}")

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

                st.session_state.text_result = result
                st.rerun()

    # 显示文字模式结果
    if st.session_state.get("text_result"):
        result = st.session_state.text_result
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
                st.download_button("⬇️ 下载视频", f.read(), file_name="text_video.mp4", mime="video/mp4", use_container_width=True)
            if result.get("cover_path") and os.path.exists(result["cover_path"]):
                with open(result["cover_path"], "rb") as f:
                    st.download_button("🖼️ 下载封面", f.read(), file_name="cover.jpg", mime="image/jpeg", use_container_width=True)

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

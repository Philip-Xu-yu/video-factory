"""
视频工厂 v3 - 分步流程 UI（对标竞品）
5 步出片：获取文案 → 仿写 → 声音克隆 → 数字人 → 分发
"""

import os
import sys
import json
import time
import tempfile
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.copywriter import extract_copy, rewrite_copy, generate_title, generate_cover_text
from core.voice_clone import voice_clone, FISH_API_KEY, FISH_VOICES
from core.pipeline import process_video, process_text_to_video
from core.templates import list_templates
from core.history import get_history, delete_history

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(BASE_DIR, "output"), exist_ok=True)

st.set_page_config(page_title="AI 视频工厂", page_icon="🎬", layout="centered")

# ===== 暗色主题 =====
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
    .platform-btn {
        display: inline-block; padding: 0.5rem 1rem; border-radius: 10px;
        border: 2px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.05);
        color: #fff; cursor: pointer; margin: 0.2rem; font-size: 0.9rem;
        transition: all 0.2s; text-align: center;
    }
    .platform-btn.active { border-color: #667eea; background: rgba(102,126,234,0.2); }
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important; font-weight: 700 !important;
        border-radius: 10px !important; border: none !important;
        padding: 0.6rem 1.5rem !important; transition: all 0.3s !important;
    }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(102,126,234,0.4); }
    .stDownloadButton > button {
        background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%) !important;
        color: white !important; font-weight: 700 !important; border-radius: 10px !important;
    }
    .stTextArea textarea, .stTextInput input {
        background: rgba(255,255,255,0.05) !important; color: #fff !important;
        border: 1px solid rgba(255,255,255,0.15) !important; border-radius: 10px !important;
    }
    .stProgress > div > div > div > div { background: linear-gradient(90deg, #667eea, #764ba2) !important; }
    .result-box {
        background: #16213e; border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px; padding: 1rem; margin: 0.5rem 0;
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
for key in ["step", "extracted_copy", "rewritten_copy", "title", "cover_text", "template"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key != "step" else 1
if not st.session_state.template:
    st.session_state.template = "douyin"

# ===== 步骤 1：获取文案 =====
st.markdown("""
<div class="step-card">
    <span class="step-num">1</span>
    <span class="step-title">获取文案</span>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🔗 粘贴视频链接", "📁 上传视频文件"])

with tab1:
    video_url = st.text_input("粘贴抖音/小红书/视频号链接", placeholder="https://...", label_visibility="collapsed")
    if st.button("⚡ 一键提取文案", key="extract_url", use_container_width=False):
        if video_url.strip():
            st.info("链接提取功能开发中，请使用「上传视频」方式")
        else:
            st.warning("请输入视频链接")

with tab2:
    uploaded_video = st.file_uploader("上传视频文件", type=["mp4", "mov", "avi", "mkv"], label_visibility="collapsed", key="step1_upload")
    if uploaded_video:
        st.video(uploaded_video)
        if st.button("⚡ 一键提取文案", key="extract_file"):
            tmp = tempfile.mkdtemp()
            path = os.path.join(tmp, uploaded_video.name)
            with open(path, "wb") as f:
                f.write(uploaded_video.read())
            with st.spinner("正在识别语音..."):
                from core.asr import transcribe
                segments = transcribe(path, model_size="base")
                full_text = " ".join([s["text"] for s in segments])
                extracted = extract_copy(full_text)
                st.session_state.extracted_copy = extracted
                st.session_state.uploaded_video_path = path
            st.success("文案提取完成!")

# 显示提取结果
if st.session_state.extracted_copy:
    st.text_area("提取的文案", st.session_state.extracted_copy, height=120, key="show_extract", disabled=True)
    if st.button("➡️ 发送到仿写", key="to_step2"):
        st.session_state.step = 2
        st.rerun()

# ===== 步骤 2：文案仿写 =====
st.markdown("""
<div class="step-card">
    <span class="step-num">2</span>
    <span class="step-title">文案仿写（100% 改写）</span>
</div>
""", unsafe_allow_html=True)

# 平台选择
platform_cols = st.columns(5)
platforms = ["🔥 抖音", "📰 公众号", "📕 小红书", "📹 视频号", "📰 新闻"]
platform_ids = ["douyin", "wechat", "xiaohongshu", "video_account", "news"]
for i, (col, pid, pname) in enumerate(zip(platform_cols, platform_ids, platforms)):
    with col:
        active = st.session_state.template == pid
        if st.button(pname, key=f"plat_{pid}", use_container_width=True):
            st.session_state.template = pid
            st.rerun()

# 输入区域
input_copy = st.text_area(
    "原文内容",
    value=st.session_state.extracted_copy or st.session_state.rewritten_copy or "",
    height=150,
    placeholder="粘贴原文，或使用上面提取的文案...",
    key="step2_input",
)

col_rewrite, col_smart = st.columns([1, 1])
with col_rewrite:
    if st.button("📝 智能仿写", use_container_width=True, key="rewrite_btn"):
        if input_copy.strip():
            with st.spinner("AI 正在仿写..."):
                rewritten = rewrite_copy(input_copy, st.session_state.template)
                st.session_state.rewritten_copy = rewritten
            st.success("仿写完成!")
        else:
            st.warning("请输入原文")
with col_smart:
    if st.button("🔄 重新生成", use_container_width=True, key="regen_btn"):
        if input_copy.strip():
            with st.spinner("重新生成中..."):
                rewritten = rewrite_copy(input_copy, st.session_state.template)
                st.session_state.rewritten_copy = rewritten
            st.success("重新生成完成!")

if st.session_state.rewritten_copy:
    st.text_area("仿写结果", st.session_state.rewritten_copy, height=150, key="show_rewrite", disabled=True)
    # 自动生成标题
    if st.button("📌 生成标题", key="gen_title"):
        with st.spinner("生成中..."):
            st.session_state.title = generate_title(st.session_state.rewritten_copy, st.session_state.template)
    if st.session_state.title:
        st.markdown(f"**标题：** {st.session_state.title}")

    if st.button("➡️ 发送到语音合成", key="to_step3"):
        st.session_state.step = 3
        st.rerun()

# ===== 步骤 3：声音克隆 =====
st.markdown("""
<div class="step-card">
    <span class="step-num">3</span>
    <span class="step-title">声音克隆</span>
</div>
""", unsafe_allow_html=True)

# 声音风格选择
if FISH_API_KEY:
    st.markdown("<span class='tag tag-active'>Fish Audio 已配置</span>", unsafe_allow_html=True)
    voice_options = list(FISH_VOICES.keys())
else:
    st.markdown("<span class='tag tag-inactive'>使用免费 TTS（设置 FISH_API_KEY 解锁高级声音）</span>", unsafe_allow_html=True)
    voice_options = ["温柔女声", "新闻播报", "活泼女声", "沉稳男声"]

selected_voice = st.selectbox("选择声音风格", voice_options, key="voice_select")

# 文本输入
tts_text = st.text_area(
    "要合成的文字",
    value=st.session_state.rewritten_copy or "",
    height=120,
    key="tts_text",
)

col_gen, col_play = st.columns([1, 1])
with col_gen:
    if st.button("🔊 生成语音", use_container_width=True, key="gen_voice"):
        if tts_text.strip():
            with st.spinner("正在合成语音..."):
                tmp_dir = tempfile.mkdtemp()
                audio_path = os.path.join(tmp_dir, "voice.mp3")
                voice_clone(tts_text, voice_style=selected_voice, output_path=audio_path)
                st.session_state.audio_path = audio_path
            st.success("语音生成完成!")
        else:
            st.warning("请输入文字")

if st.session_state.get("audio_path") and os.path.exists(st.session_state.audio_path):
    st.audio(st.session_state.audio_path)
    if st.button("➡️ 发送到数字人", key="to_step4"):
        st.session_state.step = 4
        st.rerun()

# ===== 步骤 4：数字人视频 =====
st.markdown("""
<div class="step-card">
    <span class="step-num">4</span>
    <span class="step-title">数字人视频</span>
</div>
""", unsafe_allow_html=True)

# 检查 GPU
import subprocess
try:
    gpu_check = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                               capture_output=True, text=True, timeout=5)
    gpu_name = gpu_check.stdout.strip()
    has_gpu = bool(gpu_name)
except:
    has_gpu = False
    gpu_name = ""

if has_gpu:
    st.markdown(f"<span class='tag tag-active'>GPU: {gpu_name}</span>", unsafe_allow_html=True)

    photo = st.file_uploader("上传一张正面照片", type=["jpg", "jpeg", "png"], key="face_photo")

    if photo:
        st.image(photo, width=200, caption="预览照片")

    col_gen_video, col_direct = st.columns(2)
    with col_gen_video:
        if st.button("🎬 生成数字人视频", use_container_width=True, key="gen_dh"):
            if photo and st.session_state.get("audio_path"):
                st.info("数字人生成功能需要安装 HeyGem，正在集成中...")
            else:
                st.warning("请先上传照片并生成语音")

    with col_direct:
        if st.button("⚡ 跳过数字人，直接生成", use_container_width=True, key="skip_dh"):
            st.session_state.step = 5
            st.rerun()
else:
    st.warning("未检测到 GPU，数字人功能需要 RTX 2060 以上显卡")
    st.markdown("<span class='tag tag-inactive'>需要 GPU 加速</span>", unsafe_allow_html=True)

    if st.button("⚡ 跳过数字人，直接生成", use_container_width=True, key="skip_dh_nogpu"):
        st.session_state.step = 5
        st.rerun()

# ===== 步骤 5：一键分发 =====
st.markdown("""
<div class="step-card">
    <span class="step-num">5</span>
    <span class="step-title">一键分发</span>
</div>
""", unsafe_allow_html=True)

# 平台选择
dist_cols = st.columns(4)
dist_platforms = ["🔥 抖音", "📕 小红书", "📹 视频号", "📺 B站"]
dist_keys = ["douyin", "xiaohongshu", "video_account", "bilibili"]
selected_platforms = []
for col, pname, pkey in zip(dist_cols, dist_platforms, dist_keys):
    with col:
        if st.checkbox(pname, key=f"dist_{pkey}", value=(pkey == "douyin")):
            selected_platforms.append(pkey)

# 标题和描述
pub_title = st.text_input("视频标题", value=st.session_state.title or "AI 生成视频", key="pub_title")
pub_desc = st.text_area("视频描述", value=st.session_state.rewritten_copy[:100] if st.session_state.rewritten_copy else "", height=80, key="pub_desc")

if st.button("🚀 开始分发", use_container_width=True, key="publish"):
    if selected_platforms:
        st.info(f"分发到: {', '.join(selected_platforms)}（功能开发中，敬请期待）")
    else:
        st.warning("请选择至少一个平台")

# ===== 底部：一键全流程 =====
st.markdown("---")
st.markdown("### ⚡ 或者：一键全流程")
st.markdown("上传视频，AI 自动完成所有步骤，直接出成品")

if st.button("🚀 一键出片（全流程）", use_container_width=True, type="primary", key="full_pipeline"):
    if st.session_state.get("uploaded_video_path"):
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
            status.markdown("<span style='color:#38ef7d;'>✅ 全部完成!</span>", unsafe_allow_html=True)
            st.video(result["output_path"])
            with open(result["output_path"], "rb") as f:
                st.download_button("⬇️ 下载视频", f.read(), file_name="final_video.mp4", mime="video/mp4", use_container_width=True)
            if result.get("cover_path") and os.path.exists(result["cover_path"]):
                with open(result["cover_path"], "rb") as f:
                    st.download_button("🖼️ 下载封面", f.read(), file_name="cover.jpg", mime="image/jpeg")
            if result.get("title"):
                st.markdown(f"**📌 {result['title']}**")
    else:
        st.warning("请先在第 1 步上传视频")

# ===== 历史记录 =====
st.markdown("---")
st.markdown("### 📋 历史记录")

history = get_history(10)
if history:
    for h in history:
        col1, col2, col3 = st.columns([4, 2, 1])
        with col1:
            st.markdown(f"**{h.get('title', '未命名')}**")
            st.caption(f"{h.get('time_str', '')} | {h.get('elapsed', 0):.0f}s")
        with col2:
            if h.get("output_path") and os.path.exists(h["output_path"]):
                st.video(h["output_path"])
        with col3:
            if h.get("output_path") and os.path.exists(h["output_path"]):
                with open(h["output_path"], "rb") as f:
                    st.download_button("⬇️", f.read(),
                                       file_name=f"{h.get('task_id', 'video')}.mp4",
                                       mime="video/mp4", key=f"dl_{h.get('task_id')}")
else:
    st.info("暂无历史记录")

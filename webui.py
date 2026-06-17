"""
视频工厂 v5 - 完整版
GSAP 动画 + 数字人 + 声音克隆 + 美化 UI
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

st.set_page_config(page_title="AI 视频工厂", page_icon="🎬", layout="wide")

# ===== GSAP + 高级样式 =====
st.markdown("""
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        font-family: 'Inter', -apple-system, sans-serif;
    }

    /* 标题区域 */
    .hero-section {
        text-align: center;
        padding: 3rem 2rem 2rem;
        position: relative;
        overflow: hidden;
    }
    .hero-section::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle at 30% 50%, rgba(102,126,234,0.15) 0%, transparent 50%),
                    radial-gradient(circle at 70% 50%, rgba(118,75,162,0.1) 0%, transparent 50%);
        animation: heroGlow 8s ease-in-out infinite alternate;
    }
    @keyframes heroGlow {
        0% { transform: translate(0, 0) rotate(0deg); }
        100% { transform: translate(-5%, 5%) rotate(3deg); }
    }

    .main-title {
        font-size: 3rem !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, #fff 0%, #a78bfa 50%, #f472b6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem !important;
        position: relative;
        letter-spacing: -0.03em;
    }
    .sub-title {
        color: rgba(255,255,255,0.6) !important;
        font-size: 1.1rem !important;
        margin-bottom: 2rem !important;
    }

    /* 步骤卡片 */
    .step-card {
        background: rgba(255,255,255,0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .step-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #667eea, #764ba2, #f472b6);
        opacity: 0;
        transition: opacity 0.3s;
    }
    .step-card:hover::before { opacity: 1; }
    .step-card:hover {
        border-color: rgba(102,126,234,0.3);
        box-shadow: 0 8px 32px rgba(102,126,234,0.1);
        transform: translateY(-2px);
    }

    .step-num {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border-radius: 10px;
        font-weight: 700;
        font-size: 0.9rem;
        margin-right: 0.8rem;
    }
    .step-title {
        color: #fff !important;
        font-size: 1.1rem;
        font-weight: 600;
        display: inline;
    }
    .step-desc {
        color: rgba(255,255,255,0.5);
        font-size: 0.85rem;
        margin-top: 0.3rem;
        margin-left: 2.8rem;
    }

    /* 按钮 */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 0.7rem 1.8rem !important;
        transition: all 0.3s !important;
        position: relative;
        overflow: hidden;
    }
    .stButton > button::after {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s;
    }
    .stButton > button:hover::after { left: 100%; }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(102,126,234,0.4) !important;
    }

    .stDownloadButton > button {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: 12px !important;
    }

    /* 输入框 */
    .stTextArea textarea, .stTextInput input {
        background: rgba(255,255,255,0.05) !important;
        color: #fff !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important;
        transition: border-color 0.3s !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 2px rgba(102,126,234,0.2) !important;
    }

    /* 进度条 */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea, #764ba2, #f472b6) !important;
        border-radius: 10px !important;
    }

    /* 下载区域 */
    .download-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 0.5rem 0;
    }

    /* 历史记录 */
    .history-item {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: all 0.2s;
    }
    .history-item:hover {
        background: rgba(255,255,255,0.06);
        border-color: rgba(102,126,234,0.3);
    }

    /* 标签 */
    .tag {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    .tag-purple { background: rgba(102,126,234,0.2); color: #a78bfa; }
    .tag-green { background: rgba(52,211,153,0.2); color: #34d399; }
    .tag-orange { background: rgba(251,146,60,0.2); color: #fb923c; }

    /* 分割线 */
    .gradient-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
        margin: 2rem 0;
    }

    /* 隐藏 Streamlit 默认元素 */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ===== 标题 =====
st.markdown("""
<div class="hero-section">
    <h1 class="main-title">🎬 AI 视频工厂</h1>
    <p class="sub-title">5 步自动出片，从文案到发布</p>
</div>
""", unsafe_allow_html=True)

# ===== 初始化 session =====
for key in ["extracted_copy", "rewritten_copy", "title", "cover_text", "template",
            "audio_path", "uploaded_video_path", "voice_style", "result", "text_result"]:
    if key not in st.session_state:
        st.session_state[key] = ""
if not st.session_state.template:
    st.session_state.template = "douyin"


# ===== 工具函数 =====
def get_template_name(template_id, templates):
    for t in templates:
        if t["id"] == template_id:
            return f"{t['name']} - {t['desc']}"
    return "抖音热门"


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
    <div class="step-card">
        <span class="step-num">1</span>
        <span class="step-title">上传视频，提取文案</span>
        <div class="step-desc">上传口播视频，AI 自动识别语音并提取文案</div>
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
                try:
                    segments = transcribe(path, model_size="base")
                    full_text = " ".join([s["text"] for s in segments])
                    st.session_state.extracted_copy = full_text
                    st.session_state.uploaded_video_path = path
                    st.success("文案提取完成!")
                except Exception as e:
                    st.error(f"识别失败: {e}")

    if st.session_state.extracted_copy:
        st.text_area("提取的文案", st.session_state.extracted_copy, height=120, key="show_extract", disabled=True)

    # 步骤 2
    st.markdown("""
    <div class="step-card">
        <span class="step-num">2</span>
        <span class="step-title">选择模板，AI 仿写文案</span>
        <div class="step-desc">选择目标平台风格，AI 自动改写文案并生成标题</div>
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
                try:
                    result = generate_all_copy(text_to_rewrite, st.session_state.template)
                    st.session_state.rewritten_copy = result["copy"]
                    st.session_state.title = result["title"]
                    st.session_state.cover_text = result
                    st.success("仿写完成!")
                except Exception as e:
                    st.error(f"仿写失败: {e}")
        else:
            st.warning("请先在第 1 步上传视频提取文案")

    if st.session_state.rewritten_copy:
        st.text_area("仿写结果", st.session_state.rewritten_copy, height=150, key="show_rewrite", disabled=True)
        if st.session_state.title:
            st.markdown(f"**📌 标题：** {st.session_state.title}")

    # 步骤 3
    st.markdown("""
    <div class="step-card">
        <span class="step-num">3</span>
        <span class="step-title">选择声音，生成配音</span>
        <div class="step-desc">选择声音风格，AI 用你的声音生成配音</div>
    </div>
    """, unsafe_allow_html=True)

    voice_options = list(FISH_VOICES.keys()) if FISH_API_KEY else ["温柔女声", "新闻播报", "活泼女声", "沉稳男声"]
    selected_voice = st.selectbox("选择声音风格", voice_options, key="voice_select")

    if st.button("🔊 生成语音", key="gen_voice"):
        text = st.session_state.rewritten_copy or ""
        if text.strip():
            with st.spinner("正在合成语音..."):
                try:
                    tmp_dir = tempfile.mkdtemp()
                    audio_path = os.path.join(tmp_dir, "voice.mp3")
                    voice_clone(text, voice_style=selected_voice, output_path=audio_path)
                    st.session_state.audio_path = audio_path
                    st.session_state.voice_style = selected_voice
                    st.success("语音生成完成!")
                except Exception as e:
                    st.error(f"语音合成失败: {e}")
        else:
            st.warning("请先仿写文案")

    if st.session_state.get("audio_path") and os.path.exists(st.session_state.audio_path):
        st.audio(st.session_state.audio_path)

    # 步骤 4：数字人
    st.markdown("""
    <div class="step-card">
        <span class="step-num">4</span>
        <span class="step-title">数字人视频</span>
        <div class="step-desc">上传照片，AI 生成数字人说话视频</div>
    </div>
    """, unsafe_allow_html=True)

    # GPU 检测
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
        st.markdown(f"""<span class="tag tag-green">✓ GPU: {gpu_name}</span>""", unsafe_allow_html=True)

        col_photo, col_video = st.columns(2)
        with col_photo:
            photo = st.file_uploader("上传正面照片", type=["jpg", "jpeg", "png"], key="face_photo")
            if photo:
                st.image(photo, width=200, caption="预览照片")
        with col_video:
            st.markdown("""
            <div style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:2rem;text-align:center;height:200px;display:flex;flex-direction:column;align-items:center;justify-content:center;">
                <div style="font-size:2rem;margin-bottom:0.5rem;">🎬</div>
                <div style="color:rgba(255,255,255,0.7);font-size:0.9rem;">数字人视频预览</div>
                <div style="color:rgba(255,255,255,0.4);font-size:0.75rem;margin-top:0.3rem;">上传照片后自动生成</div>
            </div>
            """, unsafe_allow_html=True)

        if st.button("🎬 生成数字人视频", use_container_width=True, key="gen_dh"):
            if photo and st.session_state.get("audio_path"):
                with st.spinner("正在生成数字人视频...（需要 1-3 分钟）"):
                    try:
                        # 尝试调用 HeyGem API（本地部署）
                        from core.digital_human import generate_digital_human
                        dh_result = generate_digital_human(
                            photo_path=photo,
                            audio_path=st.session_state.audio_path,
                            output_dir=os.path.join(BASE_DIR, "output"),
                        )
                        if dh_result.get("success"):
                            st.session_state.dh_video = dh_result["video_path"]
                            st.success("数字人视频生成完成!")
                        else:
                            st.warning(dh_result.get("error", "数字人生成失败"))
                    except ImportError:
                        st.info("数字人模块正在集成中，当前可使用「跳过数字人」直接生成视频")
                    except Exception as e:
                        st.error(f"数字人生成失败: {e}")
            else:
                st.warning("请先上传照片并生成语音")
    else:
        st.markdown("""
        <div style="background:rgba(251,146,60,0.1);border:1px solid rgba(251,146,60,0.3);border-radius:12px;padding:1.5rem;margin:1rem 0;">
            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">
                <span style="color:#fb923c;font-weight:600;">⚠️ 未检测到 GPU</span>
            </div>
            <div style="color:rgba(255,255,255,0.6);font-size:0.85rem;">
                数字人功能需要 GPU 加速。当前可跳过数字人，直接生成口播视频。
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 步骤 5：一键出片
    st.markdown("""
    <div class="step-card">
        <span class="step-num">5</span>
        <span class="step-title">一键出片</span>
        <div class="step-desc">AI 自动完成剪辑、字幕、配乐、封面，直接出成品</div>
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
                    status.markdown(f"<span style='color:#a78bfa;font-weight:500;'>{msg}</span>", unsafe_allow_html=True)

                with st.spinner("正在处理..."):
                    result = process_video(st.session_state.uploaded_video_path, st.session_state.template, output_dir, progress_callback=update)

                if "error" in result:
                    st.error(f"失败: {result['error']}")
                else:
                    progress.progress(100)
                    status.markdown("<span style='color:#34d399;font-weight:600;'>✅ 完成!</span>", unsafe_allow_html=True)
                    st.session_state.result = result
                    st.rerun()
            else:
                st.warning("请先在第 1 步上传视频")

    with col2:
        if st.button("🔄 重新开始", use_container_width=True, key="regen"):
            for k in ["extracted_copy", "rewritten_copy", "title", "result", "audio_path", "uploaded_video_path"]:
                st.session_state[k] = ""
            st.rerun()

    # 显示结果
    if st.session_state.get("result"):
        result = st.session_state.result

        st.markdown("""<div class="gradient-divider"></div>""", unsafe_allow_html=True)
        st.markdown("### 🎉 成品")

        col_v, col_d = st.columns([3, 2])
        with col_v:
            if os.path.exists(result["output_path"]):
                st.video(result["output_path"])
        with col_d:
            if result.get("title"):
                st.markdown(f"**📌 {result['title']}**")
            if result.get("copy"):
                with st.expander("📝 AI 文案"):
                    st.text(result["copy"])

            st.markdown("""<div class="gradient-divider"></div>""", unsafe_allow_html=True)
            st.markdown("**下载**")

            if os.path.exists(result["output_path"]):
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
    <div class="step-card">
        <span class="step-num">1</span>
        <span class="step-title">输入内容</span>
        <div class="step-desc">输入你想说的内容，AI 自动生成配音+字幕+视频</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📌 选择模板")
    templates = list_templates()
    cols = st.columns(4)
    for i, tmpl in enumerate(templates):
        with cols[i]:
            if st.button(f"{tmpl['name']}", key=f"tt_{tmpl['id']}", use_container_width=True):
                st.session_state["template_text"] = tmpl["id"]
                st.rerun()
    st.caption(f"当前模板：{get_template_name(st.session_state.get('template_text', 'douyin'), templates)}")

    st.markdown("### ✍️ 输入文字")
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
                status.markdown(f"<span style='color:#a78bfa;font-weight:500;'>{msg}</span>", unsafe_allow_html=True)

            with st.spinner("正在生成..."):
                result = process_text_to_video(text, st.session_state.get("template_text", "douyin"), output_dir, progress_callback=update)

            if "error" in result:
                st.error(f"失败: {result['error']}")
            else:
                progress.progress(100)
                status.markdown("<span style='color:#34d399;font-weight:600;'>✅ 完成!</span>", unsafe_allow_html=True)
                st.session_state.text_result = result
                st.rerun()

    if st.session_state.get("text_result"):
        result = st.session_state.text_result
        st.markdown("""<div class="gradient-divider"></div>""", unsafe_allow_html=True)
        st.markdown("### 🎉 成品")

        col_v, col_d = st.columns([3, 2])
        with col_v:
            if os.path.exists(result["output_path"]):
                st.video(result["output_path"])
        with col_d:
            if result.get("title"):
                st.markdown(f"**📌 {result['title']}**")
            if result.get("copy"):
                with st.expander("📝 AI 文案"):
                    st.text(result["copy"])

            st.markdown("""<div class="gradient-divider"></div>""", unsafe_allow_html=True)
            st.markdown("**下载**")

            if os.path.exists(result["output_path"]):
                with open(result["output_path"], "rb") as f:
                    st.download_button("⬇️ 下载视频", f.read(), file_name="text_video.mp4", mime="video/mp4", use_container_width=True)
            if result.get("cover_path") and os.path.exists(result["cover_path"]):
                with open(result["cover_path"], "rb") as f:
                    st.download_button("🖼️ 下载封面", f.read(), file_name="cover.jpg", mime="image/jpeg", use_container_width=True)


# ===== 历史记录 =====
st.markdown("""<div class="gradient-divider"></div>""", unsafe_allow_html=True)
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

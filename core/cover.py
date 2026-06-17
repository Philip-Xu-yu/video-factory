"""
封面模块 - 用 Pillow 生成有设计感的封面
"""

import os
import subprocess
from pathlib import Path
from loguru import logger

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("Pillow 未安装，封面功能降级")


def _get_font(size: int) -> "ImageFont.FreeTypeFont":
    """获取中文字体"""
    from core.font_utils import get_font_path
    path = get_font_path()
    if path and os.path.exists(path):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def generate_cover(video_path: str, output_path: str,
                   main_title: str, sub_title: str = "") -> str:
    """生成视频封面"""
    if not HAS_PIL:
        return _fallback_cover(video_path, output_path, main_title, sub_title)

    # 截取视频帧作为背景
    frame_path = output_path.replace(".jpg", "_frame.jpg")
    _extract_frame(video_path, frame_path)

    if not os.path.exists(frame_path):
        # 没有帧就生成渐变背景
        frame_path = output_path.replace(".jpg", "_bg.jpg")
        _create_gradient_bg(frame_path)

    try:
        # 打开背景图
        img = Image.open(frame_path).convert("RGB")
        img = img.resize((1080, 1920), Image.LANCZOS)

        # 高斯模糊背景
        img = img.filter(ImageFilter.GaussianBlur(radius=8))

        # 添加半透明遮罩
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 120))
        img = Image.composite(Image.new("RGB", img.size, (0, 0, 0)), img.convert("RGB"), overlay.split()[3])

        draw = ImageDraw.Draw(img)

        # 默认位置（居中）
        y = 1920 // 2 - 60
        th = 0

        # 主标题
        if main_title:
            font_main = _get_font(72)
            bbox = draw.textbbox((0, 0), main_title, font=font_main)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (1080 - tw) // 2
            y = (1920 - th) // 2 - 60

            draw.text((x + 3, y + 3), main_title, fill=(0, 0, 0), font=font_main)
            draw.text((x, y), main_title, fill=(255, 255, 255), font=font_main)

        # 副标题
        if sub_title:
            font_sub = _get_font(36)
            bbox_sub = draw.textbbox((0, 0), sub_title, font=font_sub)
            tw_sub = bbox_sub[2] - bbox_sub[0]
            x_sub = (1080 - tw_sub) // 2
            y_sub = y + th + 40

            draw.text((x_sub + 2, y_sub + 2), sub_title, fill=(0, 0, 0), font=font_sub)
            draw.text((x_sub, y_sub), sub_title, fill=(255, 255, 255), font=font_sub)

        # 底部品牌标识
        font_brand = _get_font(24)
        brand = "AI 视频工厂"
        bbox_b = draw.textbbox((0, 0), brand, font=font_brand)
        tw_b = bbox_b[2] - bbox_b[0]
        draw.text(((1080 - tw_b) // 2, 1850), brand, fill=(255, 255, 255, 150), font=font_brand)

        # 保存
        img.save(output_path, "JPEG", quality=90)
        logger.info(f"Pillow 封面生成: {output_path}")

    except Exception as e:
        logger.error(f"Pillow 封面失败: {e}")
        return _fallback_cover(video_path, output_path, main_title, sub_title)
    finally:
        if os.path.exists(frame_path):
            os.remove(frame_path)

    return output_path


def _extract_frame(video_path: str, output_path: str) -> str:
    """从视频截帧"""
    probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", video_path]
    result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
    try:
        duration = float(result.stdout.strip())
    except (ValueError, AttributeError):
        duration = 10

    cmd = [
        "ffmpeg", "-y", "-ss", str(duration / 3),
        "-i", video_path, "-vframes", "1",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, timeout=30)
    return output_path if os.path.exists(output_path) else ""


def _create_gradient_bg(output_path: str) -> str:
    """创建渐变背景"""
    if not HAS_PIL:
        return ""
    img = Image.new("RGB", (1080, 1920))
    draw = ImageDraw.Draw(img)
    for y in range(1920):
        r = int(15 + (y / 1920) * 30)
        g = int(12 + (y / 1920) * 20)
        b = int(42 + (y / 1920) * 50)
        draw.line([(0, y), (1080, y)], fill=(r, g, b))
    img.save(output_path, "JPEG", quality=85)
    return output_path


def _fallback_cover(video_path: str, output_path: str, main_title: str, sub_title: str) -> str:
    """降级：FFmpeg 文字叠加"""
    import re
    safe_title = re.sub(r'[^\w\s·！？]', '', main_title)
    from core.font_utils import get_ffmpeg_font_filter
    font_filter = get_ffmpeg_font_filter()
    if not font_filter:
        return ""

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x1a1a2e:s=1080x1920:d=1",
        "-vf", (
            f"drawtext=text='{safe_title}':"
            f"{font_filter}"
            "fontsize=72:fontcolor=white:"
            "x=(w-text_w)/2:y=(h-text_h)/2:"
            "borderw=4:bordercolor=black"
        ),
        "-frames:v", "1",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, timeout=30)
    return output_path if os.path.exists(output_path) else ""

import os
import subprocess
from PIL import Image, ImageDraw

def create_app_icon():
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    iconset_dir = "AppIcon.iconset"
    os.makedirs(iconset_dir, exist_ok=True)
    
    # 绘制基础 1024x1024 高清大图
    size = 1024
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 绘制外层 macOS 风格圆角底板 (带蓝紫渐变感)
    margin = 80
    bg_box = [margin, margin, size - margin, size - margin]
    draw.rounded_rectangle(bg_box, radius=200, fill="#1E293B", outline="#3B82F6", width=20)
    
    center = (size // 2, size // 2)
    
    # 绘制靶心同心圆 (雷达准星感)
    draw.ellipse([center[0] - 280, center[1] - 280, center[0] + 280, center[1] + 280], outline="#38BDF8", width=24)
    draw.ellipse([center[0] - 180, center[1] - 180, center[0] + 180, center[1] + 180], outline="#60A5FA", width=20)
    draw.ellipse([center[0] - 80, center[1] - 80, center[0] + 80, center[1] + 80], fill="#EF4444", outline="#FCA5A5", width=12)
    
    # 绘制准星十字线
    draw.line([center[0], margin + 60, center[0], center[1] - 100], fill="#38BDF8", width=18)
    draw.line([center[0], center[1] + 100, center[0], size - margin - 60], fill="#38BDF8", width=18)
    draw.line([margin + 60, center[1], center[0] - 100, center[1]], fill="#38BDF8", width=18)
    draw.line([center[0] + 100, center[1], size - margin - 60, center[1]], fill="#38BDF8", width=18)
    
    # 生成各尺寸并保存到 iconset
    for s in [16, 32, 128, 256, 512]:
        resized = img.resize((s, s), Image.Resampling.LANCZOS)
        resized.save(f"{iconset_dir}/icon_{s}x{s}.png")
        resized_2x = img.resize((s * 2, s * 2), Image.Resampling.LANCZOS)
        resized_2x.save(f"{iconset_dir}/icon_{s}x{s}@2x.png")
        
    img.save(f"{iconset_dir}/icon_512x512@2x.png")
    
    # 调用 macOS 原生 iconutil 转换为 icns
    subprocess.run(["iconutil", "-c", "icns", iconset_dir, "-o", "AppIcon.icns"], check=True)
    
    # 清理临时 iconset
    import shutil
    shutil.rmtree(iconset_dir)
    print("✅ AppIcon.icns 生成成功！")

if __name__ == "__main__":
    create_app_icon()

import streamlit as st
import whisper
import tempfile
import os
import json
import datetime
import re

# 1. 界面设置
st.set_page_config(page_title="英语发音自动标注工具-彩色版", layout="wide")
st.title("🎬 英语视频发音规则自动标注器 (彩色特效版)")

# 2. 核心功能函数：时间转换
def format_ass_timestamp(seconds):
    td = datetime.timedelta(seconds=seconds)
    total_seconds = td.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    secs = total_seconds % 60
    return f"{hours}:{minutes:02}:{secs:05.2f}"

# 3. 核心功能：对关键字进行着色处理 (ASS格式)
def colorize_text(text):
    # 将 [ ] 里的内容标黄
    text = re.sub(r'(\[.*?\])', r'{\\1c&H00FFFF&}\1{\\1c&HFFFFFF&}', text)
    # 将 ( ) 里的内容标黄
    text = re.sub(r'(\(.*?\))', r'{\\1c&H00FFFF&}\1{\\1c&HFFFFFF&}', text)
    # 将 连读符号 ⌒ 标黄
    text = text.replace('⌒', r'{\\1c&H00FFFF&}⌒{\\1c&HFFFFFF&}')
    return text

# 4. 侧边栏
st.sidebar.header("📝 发音规则设置")
default_rules = """
{
    "paris": "I have [one]⌒day lef(t)⌒in Paris.\\n说明：[one]中o弱读，lef(t)中t吞音并连读。",
    "little": "I'm a⌒[little]⌒bi(t)⌒sad...\\n说明：[little]中li弱读，bi(t)中t吞音。"
}
"""
rules_input = st.sidebar.text_area("单词映射表", default_rules, height=300)

try:
    word_rules = json.loads(rules_input)
    word_rules = {k.lower(): v for k, v in word_rules.items()}
except:
    st.sidebar.error("JSON 格式错误")
    word_rules = {}

# 5. 主区域
uploaded_file = st.file_uploader("上传 MP4 视频", type=["mp4", "mov"])

if uploaded_file is not None and word_rules:
    st.video(uploaded_file)
    
    if st.button("开始生成彩色字幕"):
        with st.spinner('AI 正在处理并自动着色中...'):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
                tfile.write(uploaded_file.read())
                video_path = tfile.name
            
            try:
                model = whisper.load_model("base") 
                result = model.transcribe(video_path, word_timestamps=True)
                
                # ASS 文件头定义
                ass_header = "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Arial,60,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,3,2,2,10,10,80,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                
                ass_lines = []
                for segment in result['segments']:
                    for word_info in segment['words']:
                        word_clean = word_info['word'].strip().lower().replace('.', '').replace(',', '').replace('!', '')
                        if word_clean in word_rules:
                            start_t = format_ass_timestamp(word_info['start'])
                            end_t = format_ass_timestamp(word_info['end'] + 1.5) # 延长显示方便阅读
                            
                            raw_text = word_rules[word_clean].replace("发音参考：", "").replace("发音参考:", "")
                            # 调用着色函数
                            rich_text = colorize_text(raw_text).replace("\n", "\\N") 
                            
                            ass_lines.append(f"Dialogue: 0,{start_t},{end_t},Default,,0,0,0,,{rich_text}")
                
                if ass_lines:
                    full_ass = ass_header + "\n".join(ass_lines)
                    st.success("✅ 彩色字幕生成成功！")
                    st.download_button("📩 下载彩色 .ASS 字幕文件", full_ass, file_name="colored_pronunciation.ass")
                else:
                    st.warning("未匹配到关键词。")
            finally:
                if os.path.exists(video_path):
                    os.remove(video_path)
#!/usr/bin/env python3
"""
Video Concatenator Script
将指定文件夹下的所有MP4视频随机拼接成1920x1080的视频
保持原视频比例不变，可设置压缩参数
"""

import os
import random
import subprocess
import tempfile
import json
from pathlib import Path

def get_video_info(video_path):
    """获取视频信息"""
    cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json', 
        '-show_streams', str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

def find_mp4_files(directory):
    """递归查找所有MP4文件"""
    mp4_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.mp4'):
                mp4_files.append(os.path.join(root, file))
    return mp4_files

def create_video_list_file(video_files, temp_dir):
    """创建ffmpeg所需的视频列表文件"""
    list_file = os.path.join(temp_dir, 'video_list.txt')
    with open(list_file, 'w') as f:
        for video in video_files:
            # 转义路径中的特殊字符
            escaped_path = video.replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")
    return list_file

def concatenate_videos(input_dir, output_file, target_width=1920, target_height=1080, crf=23):
    """
    拼接视频
    
    Args:
        input_dir: 输入视频目录
        output_file: 输出文件路径
        target_width: 目标宽度
        target_height: 目标高度
        crf: 压缩质量参数 (0-51, 越小质量越好，23是默认值)
    """
    
    print(f"正在搜索 {input_dir} 目录下的MP4文件...")
    
    # 查找所有MP4文件
    video_files = find_mp4_files(input_dir)
    print(f"找到 {len(video_files)} 个MP4文件")
    
    if not video_files:
        print("未找到MP4文件!")
        return
    
    # 随机打乱视频顺序
    random.shuffle(video_files)
    print("已随机打乱视频顺序")
    
    # 获取第一个视频的信息作为参考
    video_info = get_video_info(video_files[0])
    video_stream = next(s for s in video_info['streams'] if s['codec_type'] == 'video')
    original_width = int(video_stream['width'])
    original_height = int(video_stream['height'])
    fps = eval(video_stream['r_frame_rate'])  # 转换分数形式的帧率
    
    print(f"原始视频分辨率: {original_width}x{original_height}")
    print(f"目标分辨率: {target_width}x{target_height}")
    print(f"帧率: {fps:.2f} fps")
    
    # 计算缩放参数以保持比例
    scale_ratio = min(target_width / original_width, target_height / original_height)
    scaled_width = int(original_width * scale_ratio)
    scaled_height = int(original_height * scale_ratio)
    
    # 确保尺寸是偶数 (H.264要求)
    scaled_width = scaled_width - (scaled_width % 2)
    scaled_height = scaled_height - (scaled_height % 2)
    
    # 计算居中位置
    pad_x = (target_width - scaled_width) // 2
    pad_y = (target_height - scaled_height) // 2
    
    print(f"缩放后尺寸: {scaled_width}x{scaled_height}")
    print(f"填充位置: x={pad_x}, y={pad_y}")
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        print("正在处理视频...")
        
        # 创建视频列表文件
        list_file = create_video_list_file(video_files, temp_dir)
        
        # 构建ffmpeg命令
        # 首先拼接所有视频，然后调整到目标分辨率
        cmd = [
            'ffmpeg', '-y',  # -y 覆盖输出文件
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-vf', f'scale={scaled_width}:{scaled_height},pad={target_width}:{target_height}:{pad_x}:{pad_y}:black',
            '-c:v', 'libx264',
            '-crf', str(crf),
            '-preset', 'medium',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-r', str(int(fps)),  # 设置输出帧率
            output_file
        ]
        
        print("开始拼接视频...")
        print(f"使用命令: {' '.join(cmd)}")
        
        # 执行ffmpeg命令
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"视频拼接完成! 输出文件: {output_file}")
            print(f"压缩参数 CRF: {crf} (值越小质量越好)")
        except subprocess.CalledProcessError as e:
            print(f"拼接失败: {e}")
            print(f"错误输出: {e.stderr}")
            return False
    
    return True

def main():
    # 配置参数
    input_directory = "/Users/bytedance/Downloads/NIPS2025_supp/CoA_eval_video_compressed"
    output_file = "/Users/bytedance/Downloads/concatenated_video_1920x1080.mp4"
    
    # 视频参数
    target_width = 1920
    target_height = 1080
    crf = 23  # 压缩质量 (0-51, 推荐18-28，23是默认值)
    
    print("=== 视频拼接工具 ===")
    print(f"输入目录: {input_directory}")
    print(f"输出文件: {output_file}")
    print(f"目标分辨率: {target_width}x{target_height}")
    print(f"压缩质量 CRF: {crf}")
    print("")
    
    # 检查输入目录是否存在
    if not os.path.exists(input_directory):
        print(f"错误: 输入目录不存在: {input_directory}")
        return
    
    # 检查ffmpeg是否可用
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("错误: 系统中未找到ffmpeg，请先安装ffmpeg")
        print("安装方法: brew install ffmpeg")
        return
    
    # 执行拼接
    success = concatenate_videos(
        input_directory, 
        output_file, 
        target_width, 
        target_height, 
        crf
    )
    
    if success:
        print("\n=== 拼接完成 ===")
        # 显示输出文件信息
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
            print(f"文件大小: {file_size:.2f} MB")

if __name__ == "__main__":
    main() 
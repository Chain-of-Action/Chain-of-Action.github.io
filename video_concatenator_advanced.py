#!/usr/bin/env python3
"""
Advanced Video Concatenator Script
高级视频拼接工具，支持更多自定义参数
"""

import os
import random
import subprocess
import tempfile
import json
import argparse
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
            escaped_path = video.replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")
    return list_file

def concatenate_videos_advanced(input_dir, output_file, target_width=1920, target_height=1080, 
                              crf=23, preset='medium', max_videos=None, shuffle=True,
                              background_color='black', audio_bitrate='128k'):
    """
    高级视频拼接功能
    
    Args:
        input_dir: 输入视频目录
        output_file: 输出文件路径
        target_width: 目标宽度
        target_height: 目标高度
        crf: 压缩质量参数 (0-51, 越小质量越好)
        preset: 编码预设 (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)
        max_videos: 最大视频数量限制
        shuffle: 是否随机打乱顺序
        background_color: 背景颜色
        audio_bitrate: 音频比特率
    """
    
    print(f"正在搜索 {input_dir} 目录下的MP4文件...")
    
    # 查找所有MP4文件
    video_files = find_mp4_files(input_dir)
    print(f"找到 {len(video_files)} 个MP4文件")
    
    if not video_files:
        print("未找到MP4文件!")
        return False
    
    # 限制视频数量
    if max_videos and len(video_files) > max_videos:
        video_files = video_files[:max_videos]
        print(f"限制使用前 {max_videos} 个视频")
    
    # 随机打乱视频顺序
    if shuffle:
        random.shuffle(video_files)
        print("已随机打乱视频顺序")
    
    # 获取第一个视频的信息作为参考
    video_info = get_video_info(video_files[0])
    video_stream = next(s for s in video_info['streams'] if s['codec_type'] == 'video')
    original_width = int(video_stream['width'])
    original_height = int(video_stream['height'])
    fps = eval(video_stream['r_frame_rate'])
    
    print(f"原始视频分辨率: {original_width}x{original_height}")
    print(f"目标分辨率: {target_width}x{target_height}")
    print(f"帧率: {fps:.2f} fps")
    print(f"编码预设: {preset}")
    print(f"压缩质量 CRF: {crf}")
    
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
    print(f"背景颜色: {background_color}")
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        print("正在处理视频...")
        
        # 创建视频列表文件
        list_file = create_video_list_file(video_files, temp_dir)
        
        # 构建ffmpeg命令
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-vf', f'scale={scaled_width}:{scaled_height},pad={target_width}:{target_height}:{pad_x}:{pad_y}:{background_color}',
            '-c:v', 'libx264',
            '-crf', str(crf),
            '-preset', preset,
            '-c:a', 'aac',
            '-b:a', audio_bitrate,
            '-r', str(int(fps)),
            output_file
        ]
        
        print("开始拼接视频...")
        print(f"使用的视频文件数: {len(video_files)}")
        
        # 执行ffmpeg命令
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"视频拼接完成! 输出文件: {output_file}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"拼接失败: {e}")
            print(f"错误输出: {e.stderr}")
            return False

def main():
    parser = argparse.ArgumentParser(description='高级视频拼接工具')
    parser.add_argument('--input', '-i', required=True, help='输入视频目录')
    parser.add_argument('--output', '-o', required=True, help='输出视频文件路径')
    parser.add_argument('--width', '-w', type=int, default=1920, help='目标宽度 (默认: 1920)')
    parser.add_argument('--height', type=int, default=1080, help='目标高度 (默认: 1080)')
    parser.add_argument('--crf', type=int, default=23, help='压缩质量 0-51, 越小质量越好 (默认: 23)')
    parser.add_argument('--preset', default='medium', 
                       choices=['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow'],
                       help='编码预设 (默认: medium)')
    parser.add_argument('--max-videos', type=int, help='最大视频数量限制')
    parser.add_argument('--no-shuffle', action='store_true', help='不随机打乱视频顺序')
    parser.add_argument('--background', default='black', help='背景颜色 (默认: black)')
    parser.add_argument('--audio-bitrate', default='128k', help='音频比特率 (默认: 128k)')
    
    args = parser.parse_args()
    
    print("=== 高级视频拼接工具 ===")
    print(f"输入目录: {args.input}")
    print(f"输出文件: {args.output}")
    print(f"目标分辨率: {args.width}x{args.height}")
    print(f"压缩质量 CRF: {args.crf}")
    print(f"编码预设: {args.preset}")
    print(f"随机顺序: {not args.no_shuffle}")
    if args.max_videos:
        print(f"最大视频数: {args.max_videos}")
    print("")
    
    # 检查输入目录是否存在
    if not os.path.exists(args.input):
        print(f"错误: 输入目录不存在: {args.input}")
        return
    
    # 检查ffmpeg是否可用
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("错误: 系统中未找到ffmpeg，请先安装ffmpeg")
        return
    
    # 执行拼接
    success = concatenate_videos_advanced(
        args.input, 
        args.output, 
        args.width, 
        args.height, 
        args.crf,
        args.preset,
        args.max_videos,
        not args.no_shuffle,
        args.background,
        args.audio_bitrate
    )
    
    if success:
        print("\n=== 拼接完成 ===")
        if os.path.exists(args.output):
            file_size = os.path.getsize(args.output) / (1024 * 1024)  # MB
            print(f"文件大小: {file_size:.2f} MB")

if __name__ == "__main__":
    main() 
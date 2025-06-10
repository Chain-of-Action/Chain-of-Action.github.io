#!/usr/bin/env python3
"""
Video Grid Generator
将多个MP4视频排列成网格形式，同时播放
- 将原视频裁剪为正方形（以短边为准，中心裁剪）
- 随机排列视频位置
- 所有视频循环播放
- 输出无音频
"""

import os
import random
import subprocess
import tempfile
import json
import math
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

def calculate_optimal_grid(num_videos, target_width=1920, target_height=1080):
    """计算最佳网格布局"""
    target_ratio = target_width / target_height
    best_ratio_diff = float('inf')
    best_layout = None
    
    for rows in range(1, 20):
        cols = math.ceil(num_videos / rows)
        if rows * cols >= num_videos:
            grid_ratio = cols / rows
            ratio_diff = abs(grid_ratio - target_ratio)
            
            cell_width = target_width // cols
            cell_height = target_height // rows
            
            if ratio_diff < best_ratio_diff:
                best_ratio_diff = ratio_diff
                best_layout = (rows, cols, cell_width, cell_height)
    
    return best_layout

def create_video_grid(input_dir, output_file, target_width=1920, target_height=1080, 
                     duration=None, shuffle=True, grid_layout=None):
    """
    创建视频网格
    
    Args:
        input_dir: 输入视频目录
        output_file: 输出文件路径
        target_width: 目标宽度
        target_height: 目标高度
        duration: 输出视频时长（秒），None为自动
        shuffle: 是否随机排列
        grid_layout: 强制指定网格布局 (rows, cols)
    """
    
    print(f"正在搜索 {input_dir} 目录下的MP4文件...")
    
    # 查找所有MP4文件
    video_files = find_mp4_files(input_dir)
    print(f"找到 {len(video_files)} 个MP4文件")
    
    if not video_files:
        print("未找到MP4文件!")
        return False
    
    # 随机打乱视频顺序
    if shuffle:
        random.shuffle(video_files)
        print("已随机打乱视频顺序")
    
    # 计算网格布局
    if grid_layout:
        rows, cols = grid_layout
        cell_width = target_width // cols
        cell_height = target_height // rows
    else:
        rows, cols, cell_width, cell_height = calculate_optimal_grid(len(video_files), target_width, target_height)
    
    print(f"网格布局: {rows}x{cols}")
    print(f"单元格大小: {cell_width}x{cell_height}")
    print(f"总单元格数: {rows * cols} (使用{len(video_files)}个)")
    
    # 获取第一个视频的信息
    video_info = get_video_info(video_files[0])
    video_stream = next(s for s in video_info['streams'] if s['codec_type'] == 'video')
    original_width = int(video_stream['width'])
    original_height = int(video_stream['height'])
    fps = eval(video_stream.get('r_frame_rate', '30/1'))
    
    print(f"原始视频分辨率: {original_width}x{original_height}")
    print(f"帧率: {fps:.2f} fps")
    
    # 计算正方形裁剪参数（以短边为准）
    square_size = min(original_width, original_height)
    crop_x = (original_width - square_size) // 2
    crop_y = (original_height - square_size) // 2
    
    print(f"裁剪为正方形: {square_size}x{square_size}")
    print(f"裁剪偏移: x={crop_x}, y={crop_y}")
    
    # 设置默认时长
    if duration is None:
        duration = 30  # 默认30秒
    
    print(f"输出时长: {duration}秒")
    
    # 构建ffmpeg命令
    cmd = ['ffmpeg', '-y']
    
    # 添加输入文件（限制到网格大小）
    used_videos = video_files[:rows * cols]
    for i, video_file in enumerate(used_videos):
        cmd.extend(['-stream_loop', '-1', '-i', video_file])  # -stream_loop -1 表示无限循环
    
    # 构建复杂滤镜
    filter_complex = []
    
    # 为每个视频创建处理链：裁剪 -> 缩放
    for i in range(len(used_videos)):
        # 裁剪为正方形并缩放到单元格大小
        filter_complex.append(
            f"[{i}:v]crop={square_size}:{square_size}:{crop_x}:{crop_y},scale={cell_width}:{cell_height}[v{i}]"
        )
    
    # 创建网格布局
    # 先创建每一行
    rows_inputs = []
    for row in range(rows):
        row_videos = []
        for col in range(cols):
            video_idx = row * cols + col
            if video_idx < len(used_videos):
                row_videos.append(f"[v{video_idx}]")
            else:
                # 如果视频不够，创建黑色填充
                filter_complex.append(f"color=black:{cell_width}x{cell_height}:duration={duration}[black{video_idx}]")
                row_videos.append(f"[black{video_idx}]")
        
        # 水平拼接这一行
        if len(row_videos) > 1:
            row_input = "".join(row_videos)
            filter_complex.append(f"{row_input}hstack=inputs={len(row_videos)}[row{row}]")
            rows_inputs.append(f"[row{row}]")
        else:
            rows_inputs.append(row_videos[0])
    
    # 垂直拼接所有行
    if len(rows_inputs) > 1:
        rows_input = "".join(rows_inputs)
        filter_complex.append(f"{rows_input}vstack=inputs={len(rows_inputs)}[final]")
        output_map = "[final]"
    else:
        output_map = rows_inputs[0]
    
    # 添加滤镜到命令
    cmd.extend(['-filter_complex', ';'.join(filter_complex)])
    
    # 输出设置
    cmd.extend([
        '-map', output_map,  # 使用处理后的视频
        '-t', str(duration),  # 设置时长
        '-c:v', 'libx264',
        '-crf', '23',
        '-preset', 'medium',
        '-r', str(int(fps)),
        '-an',  # 不包含音频
        output_file
    ])
    
    print("开始生成视频网格...")
    print("这可能需要一些时间...")
    
    # 执行ffmpeg命令
    try:
        print(f"执行命令: {' '.join(cmd[:10])}... (命令太长，仅显示前10个参数)")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"视频网格生成完成! 输出文件: {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"生成失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def main():
    # 配置参数
    input_directory = "/Users/bytedance/Downloads/NIPS2025_supp/CoA_eval_video_compressed"
    output_file = "/Users/bytedance/Downloads/video_grid_1920x1080.mp4"
    
    # 视频参数
    target_width = 1920
    target_height = 1080
    duration = 30  # 30秒输出
    
    print("=== 视频网格生成工具 ===")
    print(f"输入目录: {input_directory}")
    print(f"输出文件: {output_file}")
    print(f"目标分辨率: {target_width}x{target_height}")
    print(f"输出时长: {duration}秒")
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
    
    # 执行网格生成
    success = create_video_grid(
        input_directory, 
        output_file, 
        target_width, 
        target_height, 
        duration,
        shuffle=True
    )
    
    if success:
        print("\n=== 生成完成 ===")
        # 显示输出文件信息
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
            print(f"文件大小: {file_size:.2f} MB")

if __name__ == "__main__":
    main() 
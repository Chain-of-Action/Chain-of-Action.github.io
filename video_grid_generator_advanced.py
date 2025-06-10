#!/usr/bin/env python3
"""
Advanced Video Grid Generator
高级视频网格生成工具，支持命令行参数自定义
"""

import os
import random
import subprocess
import json
import math
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

def create_video_grid_advanced(input_dir, output_file, target_width=1920, target_height=1080, 
                              duration=30, shuffle=True, grid_layout=None, crf=23, 
                              preset='medium', max_videos=None, crop_mode='center'):
    """
    创建视频网格 - 高级版本
    
    Args:
        input_dir: 输入视频目录
        output_file: 输出文件路径
        target_width: 目标宽度
        target_height: 目标高度
        duration: 输出视频时长（秒）
        shuffle: 是否随机排列
        grid_layout: 强制指定网格布局 (rows, cols)
        crf: 压缩质量参数
        preset: 编码预设
        max_videos: 最大视频数量
        crop_mode: 裁剪模式 ('center', 'top', 'bottom')
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
    
    # 计算网格布局
    if grid_layout:
        rows, cols = grid_layout
        cell_width = target_width // cols
        cell_height = target_height // rows
    else:
        rows, cols, cell_width, cell_height = calculate_optimal_grid(len(video_files), target_width, target_height)
    
    print(f"网格布局: {rows}x{cols}")
    print(f"单元格大小: {cell_width}x{cell_height}")
    print(f"总单元格数: {rows * cols} (使用{min(len(video_files), rows * cols)}个)")
    print(f"压缩质量 CRF: {crf}")
    print(f"编码预设: {preset}")
    print(f"裁剪模式: {crop_mode}")
    
    # 获取第一个视频的信息
    video_info = get_video_info(video_files[0])
    video_stream = next(s for s in video_info['streams'] if s['codec_type'] == 'video')
    original_width = int(video_stream['width'])
    original_height = int(video_stream['height'])
    fps = eval(video_stream.get('r_frame_rate', '30/1'))
    
    print(f"原始视频分辨率: {original_width}x{original_height}")
    print(f"帧率: {fps:.2f} fps")
    
    # 计算正方形裁剪参数
    square_size = min(original_width, original_height)
    
    if crop_mode == 'center':
        crop_x = (original_width - square_size) // 2
        crop_y = (original_height - square_size) // 2
    elif crop_mode == 'top':
        crop_x = (original_width - square_size) // 2
        crop_y = 0
    elif crop_mode == 'bottom':
        crop_x = (original_width - square_size) // 2
        crop_y = original_height - square_size
    else:
        crop_x = (original_width - square_size) // 2
        crop_y = (original_height - square_size) // 2
    
    print(f"裁剪为正方形: {square_size}x{square_size}")
    print(f"裁剪偏移: x={crop_x}, y={crop_y}")
    print(f"输出时长: {duration}秒")
    
    # 构建ffmpeg命令
    cmd = ['ffmpeg', '-y']
    
    # 添加输入文件（限制到网格大小）
    used_videos = video_files[:rows * cols]
    for i, video_file in enumerate(used_videos):
        cmd.extend(['-stream_loop', '-1', '-i', video_file])
    
    # 构建复杂滤镜
    filter_complex = []
    
    # 为每个视频创建处理链：裁剪 -> 缩放
    for i in range(len(used_videos)):
        filter_complex.append(
            f"[{i}:v]crop={square_size}:{square_size}:{crop_x}:{crop_y},scale={cell_width}:{cell_height}[v{i}]"
        )
    
    # 创建网格布局
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
        '-map', output_map,
        '-t', str(duration),
        '-c:v', 'libx264',
        '-crf', str(crf),
        '-preset', preset,
        '-r', str(int(fps)),
        '-an',  # 不包含音频
        output_file
    ])
    
    print("开始生成视频网格...")
    print("这可能需要一些时间...")
    
    # 执行ffmpeg命令
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"视频网格生成完成! 输出文件: {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"生成失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def main():
    parser = argparse.ArgumentParser(description='高级视频网格生成工具')
    parser.add_argument('--input', '-i', required=True, help='输入视频目录')
    parser.add_argument('--output', '-o', required=True, help='输出视频文件路径')
    parser.add_argument('--width', '-w', type=int, default=1920, help='目标宽度 (默认: 1920)')
    parser.add_argument('--height', type=int, default=1080, help='目标高度 (默认: 1080)')
    parser.add_argument('--duration', '-d', type=int, default=30, help='输出视频时长(秒) (默认: 30)')
    parser.add_argument('--grid', help='强制指定网格布局，格式: rows,cols (例如: 8,10)')
    parser.add_argument('--crf', type=int, default=23, help='压缩质量 0-51, 越小质量越好 (默认: 23)')
    parser.add_argument('--preset', default='medium', 
                       choices=['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow'],
                       help='编码预设 (默认: medium)')
    parser.add_argument('--max-videos', type=int, help='最大视频数量限制')
    parser.add_argument('--no-shuffle', action='store_true', help='不随机打乱视频顺序')
    parser.add_argument('--crop-mode', default='center', choices=['center', 'top', 'bottom'],
                       help='裁剪模式 (默认: center)')
    
    args = parser.parse_args()
    
    print("=== 高级视频网格生成工具 ===")
    print(f"输入目录: {args.input}")
    print(f"输出文件: {args.output}")
    print(f"目标分辨率: {args.width}x{args.height}")
    print(f"输出时长: {args.duration}秒")
    print(f"压缩质量 CRF: {args.crf}")
    print(f"编码预设: {args.preset}")
    print(f"随机顺序: {not args.no_shuffle}")
    if args.max_videos:
        print(f"最大视频数: {args.max_videos}")
    if args.grid:
        print(f"强制网格布局: {args.grid}")
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
    
    # 解析网格布局
    grid_layout = None
    if args.grid:
        try:
            rows, cols = map(int, args.grid.split(','))
            grid_layout = (rows, cols)
        except:
            print("错误: 网格布局格式无效，应该是 'rows,cols'")
            return
    
    # 执行网格生成
    success = create_video_grid_advanced(
        args.input, 
        args.output, 
        args.width, 
        args.height, 
        args.duration,
        not args.no_shuffle,
        grid_layout,
        args.crf,
        args.preset,
        args.max_videos,
        args.crop_mode
    )
    
    if success:
        print("\n=== 生成完成 ===")
        if os.path.exists(args.output):
            file_size = os.path.getsize(args.output) / (1024 * 1024)  # MB
            print(f"文件大小: {file_size:.2f} MB")

if __name__ == "__main__":
    main() 
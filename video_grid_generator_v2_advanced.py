#!/usr/bin/env python3
"""
Advanced Video Grid Generator V2
高级视频网格生成工具 V2，支持命令行参数自定义
- 支持不同分辨率的视频（每个视频按自身短边裁剪）
- 如果网格位置不够，随机重复使用视频填满
- 不同任务随机分布，不堆叠在一起
"""

import os
import random
import subprocess
import json
import math
import argparse
from pathlib import Path
from collections import defaultdict

def get_video_info(video_path):
    """获取视频信息"""
    cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json', 
        '-show_streams', str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

def find_mp4_files_by_task(directory):
    """按任务类型分组查找MP4文件"""
    task_videos = defaultdict(list)
    
    for root, dirs, files in os.walk(directory):
        folder_name = os.path.basename(root)
        if folder_name and folder_name != os.path.basename(directory):
            for file in files:
                if file.lower().endswith('.mp4'):
                    video_path = os.path.join(root, file)
                    task_videos[folder_name].append(video_path)
    
    return dict(task_videos)

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

def get_video_crop_params(video_path, crop_mode='center'):
    """获取单个视频的裁剪参数"""
    video_info = get_video_info(video_path)
    video_stream = next(s for s in video_info['streams'] if s['codec_type'] == 'video')
    
    width = int(video_stream['width'])
    height = int(video_stream['height'])
    fps = eval(video_stream.get('r_frame_rate', '30/1'))
    
    # 计算正方形裁剪参数（以短边为准）
    square_size = min(width, height)
    
    if crop_mode == 'center':
        crop_x = (width - square_size) // 2
        crop_y = (height - square_size) // 2
    elif crop_mode == 'top':
        crop_x = (width - square_size) // 2
        crop_y = 0
    elif crop_mode == 'bottom':
        crop_x = (width - square_size) // 2
        crop_y = height - square_size
    else:
        crop_x = (width - square_size) // 2
        crop_y = (height - square_size) // 2
    
    return {
        'original_width': width,
        'original_height': height,
        'square_size': square_size,
        'crop_x': crop_x,
        'crop_y': crop_y,
        'fps': fps
    }

def create_balanced_video_list(task_videos, grid_size, max_videos=None, shuffle=True):
    """创建平衡的视频列表，确保不同任务随机分布"""
    rows, cols = grid_size
    total_slots = rows * cols
    
    # 收集所有视频并标记任务类型
    all_videos = []
    for task_name, videos in task_videos.items():
        for video in videos:
            all_videos.append((video, task_name))
    
    # 限制视频数量
    if max_videos and len(all_videos) > max_videos:
        all_videos = all_videos[:max_videos]
        print(f"限制使用前 {max_videos} 个视频")
    
    print(f"总共有 {len(all_videos)} 个视频，需要填充 {total_slots} 个网格位置")
    
    # 如果视频数量不够，随机重复使用
    if len(all_videos) < total_slots:
        needed = total_slots - len(all_videos)
        print(f"需要随机重复 {needed} 个视频来填满网格")
        additional_videos = random.choices(all_videos, k=needed)
        all_videos.extend(additional_videos)
    
    # 随机打乱所有视频
    if shuffle:
        random.shuffle(all_videos)
        print("已随机打乱视频顺序")
    
    # 取前 total_slots 个
    selected_videos = all_videos[:total_slots]
    
    # 统计任务分布
    task_count = defaultdict(int)
    for _, task_name in selected_videos:
        task_count[task_name] += 1
    
    print("最终网格中的任务分布:")
    for task_name, count in sorted(task_count.items()):
        print(f"  {task_name}: {count} 个位置")
    
    return [video for video, _ in selected_videos]

def create_video_grid_v2_advanced(input_dir, output_file, target_width=1920, target_height=1080, 
                                 duration=30, crf=23, preset='medium', grid_layout=None,
                                 max_videos=None, shuffle=True, crop_mode='center', verbose=True):
    """
    创建视频网格 V2 - 高级版本
    """
    
    if verbose:
        print(f"正在搜索 {input_dir} 目录下的MP4文件...")
    
    # 按任务分组查找视频
    task_videos = find_mp4_files_by_task(input_dir)
    
    if not task_videos:
        print("未找到MP4文件!")
        return False
    
    # 统计视频数量
    total_videos = sum(len(videos) for videos in task_videos.values())
    if verbose:
        print(f"找到 {len(task_videos)} 个任务类型，总共 {total_videos} 个视频:")
        for task_name, videos in task_videos.items():
            print(f"  {task_name}: {len(videos)} 个视频")
    
    # 计算网格布局
    if grid_layout:
        rows, cols = grid_layout
        cell_width = target_width // cols
        cell_height = target_height // rows
    else:
        rows, cols, cell_width, cell_height = calculate_optimal_grid(total_videos, target_width, target_height)
    
    grid_size = (rows, cols)
    
    if verbose:
        print(f"\n网格布局: {rows}x{cols}")
        print(f"单元格大小: {cell_width}x{cell_height}")
        print(f"总单元格数: {rows * cols}")
        print(f"裁剪模式: {crop_mode}")
    
    # 创建平衡的视频列表
    selected_videos = create_balanced_video_list(task_videos, grid_size, max_videos, shuffle)
    
    if verbose:
        print(f"\n开始分析每个视频的裁剪参数...")
    
    # 构建ffmpeg命令
    cmd = ['ffmpeg', '-y']
    
    # 添加输入文件
    video_params = []
    for i, video_file in enumerate(selected_videos):
        cmd.extend(['-stream_loop', '-1', '-i', video_file])
        params = get_video_crop_params(video_file, crop_mode)
        video_params.append(params)
        
        if verbose:
            task_name = None
            for task, videos in task_videos.items():
                if video_file in videos:
                    task_name = task
                    break
            print(f"  视频 {i+1:2d}: {task_name:20s} | {params['original_width']:3d}x{params['original_height']:3d} → {params['square_size']:3d}x{params['square_size']:3d}")
    
    # 构建复杂滤镜
    filter_complex = []
    
    # 为每个视频创建处理链：裁剪 -> 缩放
    for i, params in enumerate(video_params):
        filter_complex.append(
            f"[{i}:v]crop={params['square_size']}:{params['square_size']}:{params['crop_x']}:{params['crop_y']},scale={cell_width}:{cell_height}[v{i}]"
        )
    
    # 创建网格布局
    rows_inputs = []
    for row in range(rows):
        row_videos = []
        for col in range(cols):
            video_idx = row * cols + col
            if video_idx < len(selected_videos):
                row_videos.append(f"[v{video_idx}]")
            else:
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
    fps = video_params[0]['fps'] if video_params else 30
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
    
    if verbose:
        print(f"\n开始生成视频网格...")
        print(f"输出时长: {duration}秒")
        print(f"压缩质量 CRF: {crf}")
        print(f"编码预设: {preset}")
        print("这可能需要一些时间...")
    
    # 执行ffmpeg命令
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if verbose:
            print(f"视频网格生成完成! 输出文件: {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"生成失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def main():
    parser = argparse.ArgumentParser(description='高级视频网格生成工具 V2')
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
    parser.add_argument('--quiet', '-q', action='store_true', help='安静模式，减少输出信息')
    
    args = parser.parse_args()
    
    verbose = not args.quiet
    
    if verbose:
        print("=== 高级视频网格生成工具 V2 ===")
        print(f"输入目录: {args.input}")
        print(f"输出文件: {args.output}")
        print(f"目标分辨率: {args.width}x{args.height}")
        print(f"输出时长: {args.duration}秒")
        print(f"压缩质量 CRF: {args.crf}")
        print(f"编码预设: {args.preset}")
        print(f"随机顺序: {not args.no_shuffle}")
        print(f"裁剪模式: {args.crop_mode}")
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
    success = create_video_grid_v2_advanced(
        args.input, 
        args.output, 
        args.width, 
        args.height, 
        args.duration,
        args.crf,
        args.preset,
        grid_layout,
        args.max_videos,
        not args.no_shuffle,
        args.crop_mode,
        verbose
    )
    
    if success and verbose:
        print("\n=== 生成完成 ===")
        if os.path.exists(args.output):
            file_size = os.path.getsize(args.output) / (1024 * 1024)  # MB
            print(f"文件大小: {file_size:.2f} MB")

if __name__ == "__main__":
    main() 
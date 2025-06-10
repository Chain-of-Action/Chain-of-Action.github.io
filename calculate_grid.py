import math

# 计算80个视频的最佳网格布局
total_videos = 80
target_width = 1920
target_height = 1080

print(f"为{total_videos}个视频计算最佳网格布局 (目标: {target_width}x{target_height})")
print("=" * 60)

# 寻找最接近16:9比例的网格
best_ratio_diff = float('inf')
best_layout = None

for rows in range(1, 15):  # 限制行数范围
    cols = math.ceil(total_videos / rows)
    if rows * cols >= total_videos:
        grid_ratio = cols / rows
        target_ratio = target_width / target_height
        ratio_diff = abs(grid_ratio - target_ratio)
        
        cell_width = target_width // cols
        cell_height = target_height // rows
        
        print(f'{rows:2d}x{cols:2d}: 网格比例={grid_ratio:.2f}, 差异={ratio_diff:.3f}, 单元格={cell_width:3d}x{cell_height:3d}')
        
        if ratio_diff < best_ratio_diff:
            best_ratio_diff = ratio_diff
            best_layout = (rows, cols, cell_width, cell_height)

print("\n" + "=" * 60)
print(f'推荐布局: {best_layout[0]}x{best_layout[1]}')
print(f'单元格大小: {best_layout[2]}x{best_layout[3]}')
print(f'总单元格数: {best_layout[0] * best_layout[1]} (需要{total_videos}个)') 
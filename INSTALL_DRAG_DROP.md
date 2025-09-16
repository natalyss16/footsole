# 拖拽功能安装说明

为了使用拖拽功能，需要安装 `tkinterdnd2` 库。

## 安装方法

### 方法1：使用pip安装
```bash
pip install tkinterdnd2
```

### 方法2：如果方法1失败，尝试从源码安装
```bash
pip install git+https://github.com/pmgagne/tkinterdnd2.git
```

### 方法3：手动下载安装
1. 访问 https://github.com/pmgagne/tkinterdnd2
2. 下载源码
3. 解压后进入目录
4. 运行：`python setup.py install`

## 验证安装
安装完成后，运行以下命令验证：
```python
import tkinterdnd2
print("tkinterdnd2 安装成功！")
```

## 使用方法
安装完成后，运行交互式可视化工具：
```bash
python programs/interactive_visualizer.py
```

## 功能特性
- 支持拖拽H5文件到蓝色区域
- 支持拖拽视频文件到绿色区域
- 拖拽时有视觉反馈
- 支持多种视频格式：.mov, .mp4, .avi, .mkv, .wmv
- 点击拖拽区域也可以选择文件

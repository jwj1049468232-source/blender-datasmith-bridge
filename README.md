# Blender Datasmith Bridge 🔄

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Blender](https://img.shields.io/badge/Blender-3.0+-orange.svg)](https://www.blender.org/)
[![Unreal Engine](https://img.shields.io/badge/Unreal%20Engine-5.0+-blue.svg)](https://www.unrealengine.com/)

> **一键同步 Blender 场景到 Unreal Engine 5，实现无缝实时工作流**

作者：**季鹋檀**

---

## ✨ 功能特性

- 🚀 **一键导出** - 静默导出 Datasmith 文件，无需弹窗确认
- 📁 **智能命名** - 自动根据集合名称命名导出文件
- 🎯 **集合导出** - 支持导出整个集合及其子集合
- 🔄 **实时同步** - 导出后自动通知 UE5 重新导入
- 🎬 **动画支持** - 导出对象变换动画
- 🔧 **修改器应用** - 可选导出前自动应用修改器
- 📂 **快速访问** - 一键打开导出目录

---

## 📦 安装方法

### 前置要求

在安装本插件之前，请确保已安装 Datasmith 导出插件：

1. 下载并安装 [blender-datasmith-export-wcc](https://github.com/0xafbf/blender-datasmith-export)
2. 在 Blender 中启用该插件

### Blender 插件安装

1. 下载本仓库的 ZIP 文件
2. 打开 Blender，进入 `Edit > Preferences > Add-ons`
3. 点击 `Install...`，选择 `blender_addon` 文件夹中的 `__init__.py`
4. 启用插件 `Import-Export: Datasmith Bridge - Blender to UE5`

### UE5 脚本安装

1. 确保已启用 **Python Editor Script Plugin**
2. 将 `ue5_script/DatasmithReimportListener.py` 复制到项目的 `Content/Python/` 文件夹
3. 在 **Output Log** 中运行：`py DatasmithReimportListener.py`
4. （可选）将脚本添加到项目启动脚本实现自动启动

---

## 🚀 使用方法

### 基础导出

1. 在 Blender 的 3D 视图中，按 `N` 键打开侧边栏
2. 切换到 **Datasmith** 标签页
3. 设置输出路径和文件名
4. 点击 **一键导出**

### 集合导出模式

1. 选中集合中的任意物体
2. 勾选 **导出整个集合**
3. 点击 **一键导出** - 将自动导出整个集合，文件名使用集合名

### UE5 实时同步

1. 勾选 **通知 UE5**
2. 设置 UE5 监听地址（默认 `127.0.0.1:19842`）
3. 确保 UE5 中已运行监听脚本
4. 导出后 UE5 将自动重新导入场景

---

## ⚙️ 配置选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| 输出路径 | 导出文件保存目录 | `//` (当前 blend 文件目录) |
| 文件名 | 导出文件名（不含扩展名） | `export` |
| 仅导出选中对象 | 只导出当前选中的物体 | `False` |
| 导出整个集合 | 导出活跃物体所在集合 | `False` |
| 应用修改器 | 导出前应用所有修改器 | `True` |
| 导出动画 | 导出对象变换动画 | `True` |
| 通知 UE5 | 导出后通知 UE5 重新导入 | `False` |
| UE5 IP | UE5 监听服务地址 | `127.0.0.1` |
| UE5 端口 | UE5 监听 UDP 端口 | `19842` |

---

## 🏗️ 项目结构

```
blender-datasmith-bridge/
├── blender_addon/
│   └── __init__.py          # Blender 插件主文件
├── ue5_script/
│   └── DatasmithReimportListener.py  # UE5 监听脚本
├── docs/                     # 文档目录
├── images/                   # 截图和演示图
├── LICENSE                   # MIT 许可证
└── README.md                 # 本文件
```

---

## 🔧 系统要求

- **Blender**: 3.0 或更高版本（已在 **5.0、5.1** 版本测试通过）
- **Unreal Engine**: 5.0 或更高版本
- **操作系统**: Windows / macOS / Linux
- **依赖**: 
  - Blender Datasmith 导出插件（如 [blender-datasmith-export-wcc](https://github.com/0xafbf/blender-datasmith-export)）
  - UE5 Python Editor Script Plugin

### 关于依赖的说明

本插件通过调用 Blender 官方的 `bpy.ops.export_scene.datasmith` 操作符实现导出功能。
用户需要预先安装提供该功能的 Datasmith 导出插件（例如 [blender-datasmith-export-wcc](https://github.com/0xafbf/blender-datasmith-export)）。

**许可证说明**：本插件仅调用 Blender 官方 API，不直接引用或链接任何 GPL 代码，因此采用 MIT 许可证独立发布。

### 兼容性说明

| Blender 版本 | 状态 | 备注 |
|-------------|------|------|
| 5.1 | ✅ 已测试 | 完全兼容 |
| 5.0 | ✅ 已测试 | 完全兼容 |
| 4.x | ⚠️ 未测试 | 理论上兼容 |
| 3.x | ⚠️ 未测试 | 理论上兼容 |

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建你的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

---

## 📝 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。

```
MIT License

Copyright (c) 2026 季鹋檀

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

## 🙏 致谢

- [Blender](https://www.blender.org/) - 开源 3D 创作套件
- [Unreal Engine](https://www.unrealengine.com/) - 世界一流的实时渲染引擎
- [Datasmith](https://www.unrealengine.com/datasmith) - Epic Games 的 Datasmith 格式
- [blender-datasmith-export-wcc](https://github.com/0xafbf/blender-datasmith-export) - 提供 Datasmith 导出功能的基础插件（GPL v3）

---

## 📧 联系方式

如有问题或建议，欢迎通过以下方式联系：

- GitHub Issues: [提交问题](https://github.com/jwj1049468232-source/blender-datasmith-bridge/issues)
- 作者: 季鹋檀

---

⭐ **如果这个项目对你有帮助，请给它一个 Star！** ⭐

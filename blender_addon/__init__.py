bl_info = {
    "name": "Datasmith Bridge - Blender to UE5",
    "author": "季鹋檀",
    "version": (1, 1, 0),
    "blender": (5, 0, 0),
    "location": "View3D > N-Panel > Datasmith",
    "description": "一键静默导出 Datasmith 并自动通知 UE5 重新导入，实现 Blender-UE5 实时同步工作流。已在 Blender 5.0、5.1 测试通过",
    "category": "Import-Export",
    "doc_url": "https://github.com/jwj1049468232-source/blender-datasmith-bridge",
    "tracker_url": "https://github.com/jwj1049468232-source/blender-datasmith-bridge/issues",
    "support": "COMMUNITY",
}

import bpy
import os
from bpy.props import StringProperty, BoolProperty, IntProperty
from bpy.types import Panel, Operator, PropertyGroup


class DatasmithQuickExportSettings(PropertyGroup):
    output_path: StringProperty(
        name="输出路径",
        description="导出文件的目录路径（支持 // 相对路径）",
        default="//",
        subtype='DIR_PATH'
    )
    
    filename: StringProperty(
        name="文件名",
        description="导出文件名（不需要扩展名）",
        default="export"
    )
    
    export_selected: BoolProperty(
        name="仅导出选中对象",
        description="只导出当前选中的对象",
        default=False
    )

    export_collection: BoolProperty(
        name="导出整个集合",
        description="选中集合里任意物体，自动导出整个集合（文件名 = 集合名）",
        default=False
    )
    
    apply_modifiers: BoolProperty(
        name="应用修改器",
        description="导出前应用所有修改器",
        default=True
    )
    
    export_animations: BoolProperty(
        name="导出动画",
        description="导出对象动画（仅变换）",
        default=True
    )

    notify_ue5: BoolProperty(
        name="通知 UE5",
        description="导出成功后通知 UE5 自动重新导入",
        default=False
    )

    ue5_ip: StringProperty(
        name="UE5 IP",
        description="UE5 监听服务的 IP 地址",
        default="127.0.0.1"
    )

    ue5_port: IntProperty(
        name="UE5 端口",
        description="UE5 监听服务的 UDP 端口",
        default=19842,
        min=1024,
        max=65535
    )


def resolve_output_dir(settings):
    """将 settings.output_path 解析为绝对目录路径"""
    blend_path = bpy.data.filepath
    blend_dir = os.path.dirname(blend_path) if blend_path else os.getcwd()

    output_dir = settings.output_path
    if output_dir.startswith("//"):
        if blend_path:
            output_dir = os.path.join(blend_dir, output_dir[2:])
        else:
            output_dir = output_dir[2:] if len(output_dir) > 2 else "."

    if not os.path.isabs(output_dir):
        output_dir = os.path.abspath(output_dir)

    return output_dir


def get_collection_name_of_object(obj, scene):
    """
    返回 obj 直接所属的第一个集合名称。
    如果物体只在场景根集合（Scene Collection）中，返回 None。
    """
    for col in scene.collection.children_recursive:
        if obj.name in col.objects:
            return col.name
    return None


def get_collection_of_object(obj, scene):
    """返回 obj 直接所属的第一个集合对象，不在任何子集合则返回 None。"""
    for col in scene.collection.children_recursive:
        if obj.name in col.objects:
            return col
    return None


def get_all_objects_in_collection(collection):
    """
    递归获取集合及其所有子集合中的全部物体。
    返回物体列表（不重复）。
    """
    objs = set()
    for obj in collection.objects:
        objs.add(obj)
    for child_col in collection.children_recursive:
        for obj in child_col.objects:
            objs.add(obj)
    return list(objs)


def notify_ue5(filepath: str, ip: str, port: int, parent_report):
    """
    导出成功后，通过 UDP 向 UE5 发送通知消息。
    消息格式：JSON {"action": "reimport", "filepath": "xxx"}
    UE5 端需要运行配套的监听服务。
    """
    import socket
    import json

    msg = json.dumps({
        "action": "reimport",
        "filepath": filepath,
        "source": "Blender"
    }, ensure_ascii=False).encode("utf-8")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        sock.sendto(msg, (ip, port))
        sock.close()
        parent_report({'INFO'}, f"已通知 UE5 ({ip}:{port})")
    except Exception as e:
        parent_report({'WARNING'}, f"通知 UE5 失败: {e}")


class DATASMITH_OT_quick_export(Operator):
    bl_idname = "datasmith.quick_export"
    bl_label = "一键导出"
    bl_description = "直接导出到指定路径，不弹窗"
    bl_options = {'REGISTER'}

    def execute(self, context):
        settings = context.scene.datasmith_quick_export

        # 解析输出目录
        output_dir = resolve_output_dir(settings)
        os.makedirs(output_dir, exist_ok=True)

        # ── 模式1：导出整个集合 ─────────────────────────────────────────
        if settings.export_collection and context.active_object:
            col = get_collection_of_object(context.active_object, context.scene)
            if col is None:
                self.report({'WARNING'}, "活跃物体不在任何子集合中，请先放入集合")
                return {'CANCELLED'}

            col_name = col.name
            filename = col_name
            if not filename.endswith(".udatasmith"):
                filename += ".udatasmith"
            filepath = os.path.normpath(os.path.join(output_dir, filename))

            self.report({'INFO'}, f"导出集合 '{col_name}' → {filepath}")

            # 临时：选中集合内所有物体，取消选中其他物体
            prev_selected = list(context.selected_objects)
            prev_active   = context.active_object

            bpy.ops.object.select_all(action='DESELECT')
            col_objs = get_all_objects_in_collection(col)
            for obj in col_objs:
                obj.select_set(True)
            # active 必须也在集合内
            if col_objs:
                context.view_layer.objects.active = col_objs[0]

            try:
                bpy.ops.export_scene.datasmith(
                    filepath=filepath,
                    export_selected=True,
                    export_animations=settings.export_animations,
                    apply_modifiers=settings.apply_modifiers,
                    minimal_export=False,
                    use_gamma_hack=False,
                    compatibility_mode=False,
                    write_metadata=True,
                    use_logging=False,
                    use_profiling=False,
                )
                self.report({'INFO'}, f"已导出到: {filepath}")
                if settings.notify_ue5:
                    notify_ue5(filepath, settings.ue5_ip, settings.ue5_port, self.report)
            except Exception as e:
                self.report({'ERROR'}, f"导出失败: {str(e)}")
                return {'CANCELLED'}
            finally:
                # 恢复原来的选择状态
                bpy.ops.object.select_all(action='DESELECT')
                for obj in prev_selected:
                    obj.select_set(True)
                context.view_layer.objects.active = prev_active

            return {'FINISHED'}

        # ── 模式2：普通导出 ────────────────────────────────────────────
        # 决定文件名
        # 如果勾选了"仅导出选中对象"且有活跃物体，用该物体所属集合名称
        filename = settings.filename
        if settings.export_selected and context.active_object:
            col_name = get_collection_name_of_object(context.active_object, context.scene)
            if col_name:
                filename = col_name
                self.report({'INFO'}, f"文件名自动设为集合名: {col_name}")

        if not filename.endswith(".udatasmith"):
            filename += ".udatasmith"

        filepath = os.path.normpath(os.path.join(output_dir, filename))

        # 检查官方操作符是否存在
        if not hasattr(bpy.ops.export_scene, 'datasmith'):
            self.report({'ERROR'},
                "未找到官方 Datasmith 插件，请在 Edit > Preferences > Add-ons 中启用 Datasmith 插件")
            return {'CANCELLED'}

        # 使用官方操作符导出，覆盖 filepath 避免弹窗
        try:
            bpy.ops.export_scene.datasmith(
                filepath=filepath,
                export_selected=settings.export_selected,
                export_animations=settings.export_animations,
                apply_modifiers=settings.apply_modifiers,
                minimal_export=False,
                use_gamma_hack=False,
                compatibility_mode=False,
                write_metadata=True,
                use_logging=False,
                use_profiling=False,
            )
            self.report({'INFO'}, f"已导出到: {filepath}")

            # 导出成功后通知 UE5
            if settings.notify_ue5:
                notify_ue5(filepath, settings.ue5_ip, settings.ue5_port, self.report)
        except RuntimeError as e:
            error_msg = str(e)
            if "context" in error_msg.lower() or "window" in error_msg.lower():
                self.report({'ERROR'}, f"导出失败，请确保在 3D 视图中执行: {error_msg}")
            else:
                self.report({'ERROR'}, f"导出失败: {error_msg}")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"导出失败: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}


class DATASMITH_OT_open_output_folder(Operator):
    bl_idname = "datasmith.open_output_folder"
    bl_label = "打开输出目录"
    bl_description = "用文件管理器打开导出目录"
    bl_options = {'REGISTER'}

    def execute(self, context):
        settings = context.scene.datasmith_quick_export

        output_dir = resolve_output_dir(settings)
        os.makedirs(output_dir, exist_ok=True)

        import subprocess
        import sys
        if os.name == 'nt':  # Windows — 不用 shell=True，避免路径注入
            subprocess.Popen(['explorer', output_dir])
        elif os.name == 'posix':
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['open', output_dir])
            else:  # Linux
                subprocess.run(['xdg-open', output_dir])

        return {'FINISHED'}


class DATASMITH_PT_quick_export_panel(Panel):
    bl_label = "Datasmith Bridge"
    bl_idname = "DATASMITH_PT_quick_export_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Datasmith'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.datasmith_quick_export

        # 路径设置
        box = layout.box()
        box.label(text="输出设置:", icon='FILE_FOLDER')
        box.prop(settings, "output_path")
        box.prop(settings, "filename")

        # 预览最终路径
        output_dir = resolve_output_dir(settings)

        # 决定预览文件名（与 execute 逻辑保持一致）
        preview_name = settings.filename
        if settings.export_selected and context.active_object:
            col_name = get_collection_name_of_object(context.active_object, context.scene)
            if col_name:
                preview_name = col_name

        if not preview_name.endswith(".udatasmith"):
            preview_name += ".udatasmith"

        preview_path = os.path.normpath(os.path.join(output_dir, preview_name))

        col = box.column()
        col.enabled = False
        col.label(text="最终路径:")
        col.label(text=preview_path)

        # 如果正在用集合名，额外提示一行
        if settings.export_selected and context.active_object:
            col_name = get_collection_name_of_object(context.active_object, context.scene)
            if col_name:
                hint = box.column()
                hint.enabled = False
                hint.label(text=f"集合名: {col_name}", icon='OUTLINER_COLLECTION')

        # 导出选项
        box = layout.box()
        box.label(text="导出选项:", icon='EXPORT')
        box.prop(settings, "export_collection")
        # 若启用"导出整个集合"，显示当前集合名
        if settings.export_collection and context.active_object:
            col = get_collection_of_object(context.active_object, context.scene)
            hint = box.column()
            hint.enabled = False
            if col:
                hint.label(text=f"将导出集合: {col.name}", icon='OUTLINER_COLLECTION')
            else:
                hint.label(text="⚠ 活跃物体不在任何子集合中", icon='ERROR')
        box.prop(settings, "export_selected")
        box.prop(settings, "apply_modifiers")
        box.prop(settings, "export_animations")

        # UE5 通知设置
        box = layout.box()
        box.label(text="UE5 联动:", icon='LINKED')
        box.prop(settings, "notify_ue5")
        if settings.notify_ue5:
            box.prop(settings, "ue5_ip")
            box.prop(settings, "ue5_port")
            hint = box.column()
            hint.enabled = False
            hint.label(text="导出后自动通知 UE5 重新导入", icon='INFO')

        # 导出按钮
        layout.separator()
        row = layout.row()
        row.scale_y = 1.5
        row.operator("datasmith.quick_export", icon='EXPORT')

        layout.operator("datasmith.open_output_folder", icon='FILE_FOLDER')


classes = (
    DatasmithQuickExportSettings,
    DATASMITH_OT_quick_export,
    DATASMITH_OT_open_output_folder,
    DATASMITH_PT_quick_export_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.datasmith_quick_export = bpy.props.PointerProperty(type=DatasmithQuickExportSettings)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.datasmith_quick_export


if __name__ == "__main__":
    register()

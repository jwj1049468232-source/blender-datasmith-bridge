# Copyright (c) 2026 季鹋檀
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Datasmith Reimport Listener for Unreal Engine 5

This script runs inside the Unreal Engine 5 editor and listens for UDP messages
from Blender to automatically reimport Datasmith scenes.

Usage:
    1. Copy this file to your UE5 project's Content/Python/ folder
    2. Enable the Python Editor Script Plugin in UE5
    3. Run the script from the Output Log: py DatasmithReimportListener.py
    4. Or add it to your project's startup scripts

Author: 季鹋檀
License: MIT
"""

import unreal
import socket
import json
import threading
import os

_listening = False
_socket = None
_thread = None
_pending_imports = []
_import_in_progress = False

def _get_filename_key(filepath):
    """Extract a unique key from filepath for matching"""
    basename = os.path.basename(filepath)
    name_without_ext = os.path.splitext(basename)[0]
    return name_without_ext.lower()

def _keys_match(file_key, path_key):
    """
    Match file key against UE path key.
    UE replaces spaces with underscores and appends _N for duplicates.
    e.g. "My Model" -> "My_Model", "My Model" (second) -> "My_Model_1"
    Strategy: normalize both sides by replacing underscores with spaces,
    then also try exact match to handle names that genuinely contain underscores.
    """
    # Exact match first (handles names with underscores like "my_model")
    if file_key == path_key:
        return True
    # UE converts spaces to underscores: "collection 1" -> "collection_1"
    # So normalize both to spaces for comparison
    if file_key.replace('_', ' ') == path_key.replace('_', ' '):
        return True
    return False

def _exit_camera_view():
    """Exit camera pilot view by executing console command"""
    try:
        # Try to exit camera pilot view using console command
        # ALT+G in UE5 is "Toggle Pilot Camera" or "Stop Piloting Camera"
        world = unreal.EditorLevelLibrary.get_editor_world()
        if world:
            # Execute console command to exit camera view
            # "TogglePilotCamera" or similar command
            unreal.SystemLibrary.execute_console_command(world, "TogglePilotCamera")
            unreal.log("[DatasmithReimport] executed TogglePilotCamera")
    except Exception as e:
        unreal.log("[DatasmithReimport] exit camera view note: " + str(e))

def _find_all_datasmith_scene_actors():
    """Find all DatasmithSceneActors in the level"""
    subsystem = unreal.EditorActorSubsystem()
    actors = subsystem.get_all_level_actors()
    datasmith_actors = []

    for actor in actors:
        if actor.get_class().get_name() == "DatasmithSceneActor":
            datasmith_actors.append(actor)

    return datasmith_actors

def _find_all_datasmith_mesh_actors():
    """Find all StaticMeshActors in /Game/Datasmith/"""
    subsystem = unreal.EditorActorSubsystem()
    actors = subsystem.get_all_level_actors()
    mesh_actors = []

    for actor in actors:
        if actor.get_class().get_name() == "StaticMeshActor":
            try:
                mesh_comp = actor.static_mesh_component
                if mesh_comp:
                    mesh = mesh_comp.get_static_mesh()
                    if mesh:
                        mesh_path = mesh.get_path_name()
                        if "/Game/Datasmith/" in mesh_path:
                            mesh_actors.append(actor)
            except:
                pass

    return mesh_actors

def _find_all_camera_actors():
    """Find all CameraActors"""
    subsystem = unreal.EditorActorSubsystem()
    actors = subsystem.get_all_level_actors()
    camera_actors = []

    for actor in actors:
        if actor.get_class().get_name() == "CameraActor":
            camera_actors.append(actor)

    return camera_actors

def _delete_actor(actor):
    """Delete an actor"""
    try:
        unreal.EditorActorSubsystem().destroy_actor(actor)
        return True
    except:
        return False

def _do_import(filepath):
    global _import_in_progress

    _import_in_progress = True
    unreal.log("[DatasmithReimport] importing: " + filepath)

    try:
        file_key = _get_filename_key(filepath)

        # Find all scene actors
        scene_actors = _find_all_datasmith_scene_actors()
        mesh_actors = _find_all_datasmith_mesh_actors()
        camera_actors = _find_all_camera_actors()
        
        target_scene_actor = None
        
        # Find actors that match this file by path name
        for scene_actor in scene_actors:
            try:
                scene_asset = scene_actor.get_editor_property('scene')
                if scene_asset:
                    scene_path = scene_asset.get_path_name()
                    # e.g. /Game/Datasmith/My_Model/My_Model.My_Model -> take [-2] -> "My_Model"
                    path_key = scene_path.split('/')[-2].lower()
                    
                    if _keys_match(file_key, path_key):
                        target_scene_actor = scene_actor
                        break
            except:
                pass

        if target_scene_actor:
            # Same file - try reimport
            unreal.log("[DatasmithReimport] same file, trying reimport...")
            
            try:
                scene_asset = target_scene_actor.get_editor_property('scene')
                scene_asset_path = scene_asset.get_path_name()
                scene_element = unreal.DatasmithSceneElement.get_existing_datasmith_scene(scene_asset_path)
                
                if scene_element:
                    result = scene_element.reimport_scene()
                    if result.import_succeed:
                        unreal.log("[DatasmithReimport] reimport SUCCESS!")
                        _import_in_progress = False
                        return
                    else:
                        unreal.log("[DatasmithReimport] reimport returned False, deleting and recreating...")
            except Exception as e:
                unreal.log("[DatasmithReimport] reimport failed: " + str(e))

        # Reimport failed - delete and fresh import
        unreal.log("[DatasmithReimport] deleting old actors...")
        
        # Only exit camera view when we're about to delete cameras
        if target_scene_actor:
            _delete_actor(target_scene_actor)
        
        # Delete all Datasmith meshes
        for mesh in mesh_actors:
            _delete_actor(mesh)
        
        # Delete ALL cameras when reimport fails - exit camera view first!
        unreal.log("[DatasmithReimport] deleting cameras...")
        _exit_camera_view()  # Exit camera view BEFORE deleting cameras
        for camera in camera_actors:
            _delete_actor(camera)

        # Fresh import
        unreal.log("[DatasmithReimport] fresh import...")
        scene = unreal.DatasmithSceneElement.construct_datasmith_scene_from_file(filepath)
        if scene:
            result = scene.import_scene("/Game/Datasmith")
            
            if result and result.import_succeed:
                unreal.log("[DatasmithReimport] import SUCCESS!")
            else:
                unreal.log("[DatasmithReimport] import result: " + str(result))

    except Exception as e:
        unreal.log_error("[DatasmithReimport] error: " + str(e))

    _import_in_progress = False

def _tick_handler(delta_time):
    global _pending_imports, _import_in_progress

    if _pending_imports and not _import_in_progress:
        filepath = _pending_imports.pop(0)
        _do_import(filepath)

    return True

def _listen():
    global _listening

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(1.0)
    sock.bind(("0.0.0.0", 19842))

    unreal.log("[DatasmithReimport] UDP ready on port 19842")

    while _listening:
        try:
            data, addr = sock.recvfrom(1024)
            msg = data.decode('utf-8')
            unreal.log("[DatasmithReimport] recv: " + msg)

            try:
                obj = json.loads(msg)
                if obj.get("action") == "reimport":
                    filepath = obj.get("filepath", "")
                    if filepath:
                        unreal.log("[DatasmithReimport] queued: " + filepath)
                        _pending_imports.append(filepath)
            except Exception as e:
                unreal.log_error("[DatasmithReimport] parse error: " + str(e))

        except socket.timeout:
            continue
        except Exception as e:
            if _listening:
                unreal.log_error("[DatasmithReimport] recv error: " + str(e))

    sock.close()

def start_listener():
    global _listening, _thread
    if _listening:
        unreal.log("[DatasmithReimport] already running")
        return

    _listening = True
    _thread = threading.Thread(target=_listen, daemon=True)
    _thread.start()

    unreal.register_slate_post_tick_callback(_tick_handler)
    unreal.log("[DatasmithReimport] started")

def stop_listener():
    global _listening
    _listening = False

    try:
        unreal.unregister_slate_post_tick_callback(_tick_handler)
    except:
        pass

    unreal.log("[DatasmithReimport] stopped")

# Auto-start when the script is loaded
start_listener()

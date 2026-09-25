# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/server_FDScript/flet_permissions.py

import flet as ft

_permission_handler = None


async def request_flet_permissions(page: ft.Page):
    global _permission_handler
    if _permission_handler is None:
        _permission_handler = ft.PermissionHandler()
        page.overlay.append(_permission_handler)
        page.update()
    ph = _permission_handler
    try:
        if hasattr(ph, 'check_permission_async'):
            notif_status = await ph.check_permission_async(ft.PermissionType.NOTIFICATION)
            if notif_status != ft.PermissionStatus.GRANTED:
                await ph.request_permission_async(ft.PermissionType.NOTIFICATION)
        else:
            notif_status = ph.check_permission(ft.PermissionType.NOTIFICATION)
            if notif_status != ft.PermissionStatus.GRANTED:
                ph.request_permission(ft.PermissionType.NOTIFICATION)
    except Exception as e:
        print(f"[Permissions] Notification error: {e}")
    try:
        if hasattr(ph, 'check_permission_async'):
            battery_status = await ph.check_permission_async(ft.PermissionType.IGNORE_BATTERY_OPTIMIZATIONS)
            if battery_status != ft.PermissionStatus.GRANTED:
                await ph.request_permission_async(ft.PermissionType.IGNORE_BATTERY_OPTIMIZATIONS)
        else:
            battery_status = ph.check_permission(ft.PermissionType.IGNORE_BATTERY_OPTIMIZATIONS)
            if battery_status != ft.PermissionStatus.GRANTED:
                ph.request_permission(ft.PermissionType.IGNORE_BATTERY_OPTIMIZATIONS)
    except Exception as e:
        print(f"[Permissions] Battery optimization error: {e}")
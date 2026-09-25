# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/__init__.py

import sys as _sys

from . import http_ops as http_ops
from . import math_ops as math_ops
from . import control_flow as control_flow
from . import functions_ops as functions_ops
from . import sync_mode_ops as sync_mode_ops

_sys.modules.setdefault('func_FDScript', _sys.modules[__name__])
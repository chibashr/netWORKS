"""
Workspace management module for the netWORKS application.
"""

from core.ui.workspace.workspace_functions import (
    show_workspace_dialog,
    on_workspace_selected,
    create_new_workspace,
    save_workspace_data,
    autosave_workspace,
    import_workspace_data,
    export_workspace_data
)

__all__ = [
    'show_workspace_dialog',
    'on_workspace_selected',
    'create_new_workspace',
    'save_workspace_data',
    'autosave_workspace',
    'import_workspace_data',
    'export_workspace_data'
] 
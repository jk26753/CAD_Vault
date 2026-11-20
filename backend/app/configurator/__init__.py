"""Table Configurator: a standalone tool that edits equations.txt and rebuilds SolidWorks.

It shares nothing with Model Vault except the FastAPI app it is mounted on.
"""
from .router import router

__all__ = ["router"]

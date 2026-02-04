"""
Workflows module - Pipeline orchestration for digest generation.
"""
from workflows.base import PersonaPipeline
from workflows.pipeline_factory import ConfigurablePipeline, create_pipelines_from_config

__all__ = [
    "PersonaPipeline",
    "ConfigurablePipeline",
    "create_pipelines_from_config",
]

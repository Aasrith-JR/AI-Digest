"""
Configuration service for the GUI application.
Handles reading and writing config.yml with proper validation.
Uses async file I/O for non-blocking operations.
"""
import yaml
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional
import logging
import aiofiles
from threading import Lock

logger = logging.getLogger(__name__)

# Thread pool for file operations
_executor = ThreadPoolExecutor(max_workers=2)
_config_lock = Lock()


def _get_config_path() -> str:
    """Get the path to config.yml, handling different working directories."""
    # Try relative path first
    if os.path.exists('resources/config.yml'):
        return 'resources/config.yml'

    # Try from project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    config_path = os.path.join(project_root, 'resources', 'config.yml')
    if os.path.exists(config_path):
        return config_path

    raise FileNotFoundError("Cannot find resources/config.yml")


async def read_config_async() -> Dict[str, Any]:
    """Read config.yml asynchronously."""
    config_path = _get_config_path()

    async with aiofiles.open(config_path, 'r', encoding='utf-8') as f:
        content = await f.read()

    return yaml.safe_load(content)


async def write_config_async(config: Dict[str, Any]) -> bool:
    """Write config.yml asynchronously with proper locking."""
    config_path = _get_config_path()

    try:
        # Create backup first
        backup_path = config_path + '.backup'
        if os.path.exists(config_path):
            async with aiofiles.open(config_path, 'r', encoding='utf-8') as f:
                backup_content = await f.read()
            async with aiofiles.open(backup_path, 'w', encoding='utf-8') as f:
                await f.write(backup_content)

        # Write new config
        yaml_content = yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False)
        async with aiofiles.open(config_path, 'w', encoding='utf-8') as f:
            await f.write(yaml_content)

        logger.info("Configuration updated successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to write config: {e}")
        # Restore backup if available
        if os.path.exists(backup_path):
            async with aiofiles.open(backup_path, 'r', encoding='utf-8') as f:
                backup_content = await f.read()
            async with aiofiles.open(config_path, 'w', encoding='utf-8') as f:
                await f.write(backup_content)
        return False


async def get_config_section(section: str) -> Optional[Dict[str, Any]]:
    """Get a specific section of the config."""
    config = await read_config_async()
    return config.get(section)


async def update_config_section(section: str, data: Dict[str, Any]) -> bool:
    """Update a specific section of the config."""
    with _config_lock:
        config = await read_config_async()
        config[section] = data
        return await write_config_async(config)


async def get_email_colors() -> Dict[str, str]:
    """Get email colors from config."""
    config = await read_config_async()
    return config.get('email_colors', {})


async def update_email_colors(colors: Dict[str, str]) -> bool:
    """Update email colors in config."""
    return await update_config_section('email_colors', colors)


async def get_pipelines() -> Dict[str, Any]:
    """Get pipelines configuration."""
    config = await read_config_async()
    return config.get('pipelines', {})


async def update_pipeline(name: str, pipeline_data: Dict[str, Any]) -> bool:
    """Update a specific pipeline configuration."""
    with _config_lock:
        config = await read_config_async()
        if 'pipelines' not in config:
            config['pipelines'] = {}
        config['pipelines'][name] = pipeline_data
        return await write_config_async(config)


async def toggle_pipeline(name: str, enabled: bool) -> bool:
    """Enable or disable a pipeline."""
    with _config_lock:
        config = await read_config_async()
        if 'pipelines' in config and name in config['pipelines']:
            config['pipelines'][name]['enabled'] = enabled
            return await write_config_async(config)
        return False


async def get_email_settings() -> Dict[str, Any]:
    """Get email delivery settings."""
    config = await read_config_async()
    return {
        'EMAIL_ENABLED': config.get('EMAIL_ENABLED', False),
        'EMAIL_SMTP_HOST': config.get('EMAIL_SMTP_HOST', ''),
        'EMAIL_SMTP_PORT': config.get('EMAIL_SMTP_PORT', 587),
        'EMAIL_FROM': config.get('EMAIL_FROM', ''),
        'EMAIL_TO': config.get('EMAIL_TO', ''),
    }


async def update_email_settings(settings: Dict[str, Any]) -> bool:
    """Update email delivery settings."""
    with _config_lock:
        config = await read_config_async()
        for key, value in settings.items():
            if key in ['EMAIL_ENABLED', 'EMAIL_SMTP_HOST', 'EMAIL_SMTP_PORT', 'EMAIL_FROM', 'EMAIL_TO']:
                config[key] = value
        return await write_config_async(config)


def read_config_sync() -> Dict[str, Any]:
    """Synchronous version for use in non-async contexts."""
    config_path = _get_config_path()
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def write_config_sync(config: Dict[str, Any]) -> bool:
    """Synchronous version for use in non-async contexts."""
    config_path = _get_config_path()
    try:
        with _config_lock:
            yaml_content = yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False)
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
        return True
    except Exception as e:
        logger.error(f"Failed to write config: {e}")
        return False

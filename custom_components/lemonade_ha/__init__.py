"""Lemonade HA integration — setup and teardown."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .client import LemonadeClient
from .const import CONF_HOST, CONF_PORT, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lemonade HA from a config entry."""
    client = LemonadeClient(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        client: LemonadeClient = hass.data[DOMAIN].pop(entry.entry_id)
        await client.close()
    return ok

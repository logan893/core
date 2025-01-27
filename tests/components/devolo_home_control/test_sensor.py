"""Tests for the devolo Home Control sensor platform."""
from unittest.mock import patch

from homeassistant.components.sensor import (
    ATTR_STATE_CLASS,
    DOMAIN,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity import EntityCategory

from . import configure_integration
from .mocks import HomeControlMock, HomeControlMockConsumption, HomeControlMockSensor


async def test_temperature_sensor(hass: HomeAssistant):
    """Test setup of a temperature sensor device."""
    entry = configure_integration(hass)
    test_gateway = HomeControlMockSensor()
    with patch(
        "homeassistant.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, HomeControlMock()],
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get(f"{DOMAIN}.test")
    assert state is not None
    assert state.state == str(
        test_gateway.devices["Test"]
        .multi_level_sensor_property["devolo.MultiLevelSensor:Test"]
        .value
    )
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.TEMPERATURE


async def test_battery_sensor(hass: HomeAssistant):
    """Test setup and state change of a battery sensor device."""
    entry = configure_integration(hass)
    er = entity_registry.async_get(hass)
    test_gateway = HomeControlMockSensor()
    test_gateway.devices["Test"].battery_level = 25
    with patch(
        "homeassistant.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, HomeControlMock()],
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get(f"{DOMAIN}.test_2")
    assert state is not None
    assert state.state == str(test_gateway.devices["Test"].battery_level)
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.BATTERY
    assert er.async_get(f"{DOMAIN}.test_2").entity_category is EntityCategory.DIAGNOSTIC

    # Emulate websocket message: value changed
    test_gateway.publisher.dispatch("Test", ("Test", 10, "battery_level"))
    await hass.async_block_till_done()
    assert hass.states.get(f"{DOMAIN}.test_2").state == "10"


async def test_consumption_sensor(hass: HomeAssistant):
    """Test setup and state change of a consumption sensor device."""
    entry = configure_integration(hass)
    test_gateway = HomeControlMockConsumption()
    with patch(
        "homeassistant.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, HomeControlMock()],
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get(f"{DOMAIN}.test_current")
    assert state is not None
    assert state.state == str(
        test_gateway.devices["Test"].consumption_property["devolo.Meter:Test"].current
    )
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.POWER

    state = hass.states.get(f"{DOMAIN}.test_total")
    assert state is not None
    assert state.state == str(
        test_gateway.devices["Test"].consumption_property["devolo.Meter:Test"].total
    )
    assert state.attributes[ATTR_STATE_CLASS] == SensorStateClass.TOTAL_INCREASING
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.ENERGY

    # Emulate websocket message: value changed
    test_gateway.devices["Test"].consumption_property["devolo.Meter:Test"].total = 50.0
    test_gateway.publisher.dispatch("Test", ("devolo.Meter:Test", 50.0))
    await hass.async_block_till_done()
    assert hass.states.get(f"{DOMAIN}.test_total").state == "50.0"

    # Emulate websocket message: device went offline
    test_gateway.devices["Test"].status = 1
    test_gateway.publisher.dispatch("Test", ("Status", False, "status"))
    await hass.async_block_till_done()
    assert hass.states.get(f"{DOMAIN}.test_current").state == STATE_UNAVAILABLE
    assert hass.states.get(f"{DOMAIN}.test_total").state == STATE_UNAVAILABLE


async def test_voltage_sensor(hass: HomeAssistant):
    """Test disabled setup of a voltage sensor device."""
    entry = configure_integration(hass)
    test_gateway = HomeControlMockConsumption()
    with patch(
        "homeassistant.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, HomeControlMock()],
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get(f"{DOMAIN}.test")
    assert state is None


async def test_sensor_change(hass: HomeAssistant):
    """Test state change of a sensor device."""
    entry = configure_integration(hass)
    test_gateway = HomeControlMockSensor()
    with patch(
        "homeassistant.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, HomeControlMock()],
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Emulate websocket message: value changed
    test_gateway.publisher.dispatch("Test", ("devolo.MultiLevelSensor:Test", 50.0))
    await hass.async_block_till_done()
    state = hass.states.get(f"{DOMAIN}.test")
    assert state.state == "50.0"

    # Emulate websocket message: device went offline
    test_gateway.devices["Test"].status = 1
    test_gateway.publisher.dispatch("Test", ("Status", False, "status"))
    await hass.async_block_till_done()
    assert hass.states.get(f"{DOMAIN}.test").state == STATE_UNAVAILABLE


async def test_remove_from_hass(hass: HomeAssistant):
    """Test removing entity."""
    entry = configure_integration(hass)
    test_gateway = HomeControlMockSensor()
    with patch(
        "homeassistant.components.devolo_home_control.HomeControl",
        side_effect=[test_gateway, HomeControlMock()],
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get(f"{DOMAIN}.test")
    assert state is not None
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass.states.async_all()) == 0
    assert test_gateway.publisher.unregister.call_count == 1

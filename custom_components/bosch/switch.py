"""
Support for water heaters connected to Bosch thermostat.

For more details about this platform, please refer to the documentation at...
"""
import logging

from bosch_thermostat_client.const import GATEWAY
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, SIGNAL_BOSCH, SWITCH, SIGNAL_SWITCH, UUID, CIRCUITS, CIRCUITS_SENSOR_NAMES


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Bosch Water heater from a config entry."""
    uuid = config_entry.data[UUID]
    data = hass.data[DOMAIN][uuid]
    enabled_switches = config_entry.data.get(SWITCH, [])
    data_switch = []
    for switch in data[GATEWAY].switches:
        data_switch.append(
            BoschSwitch(
                hass=hass,
                uuid=uuid,
                bosch_object=switch,
                gateway=data[GATEWAY],
                name=switch.name,
                attr_uri=switch.attr_id,
                domain_name="Switches",
                is_enabled=switch.attr_id in enabled_switches,
            )
        )
    for circ_type in CIRCUITS:
        circuits = data[GATEWAY].get_circuits(circ_type)
        for circuit in circuits:
            for switch in circuit.switches:
                data_switch.append(
                    CircuitSwitch(
                        hass=hass,
                        uuid=uuid,
                        bosch_object=switch,
                        gateway=data[GATEWAY],
                        name=switch.name,
                        attr_uri=switch.attr_id,
                        domain_name=circuit.name,
                        circuit_type=circ_type,
                        is_enabled=switch.attr_id in enabled_switches,
                    )
                )
    data[SWITCH] = data_switch
    async_add_entities(data[SWITCH])
    async_dispatcher_send(hass, SIGNAL_BOSCH)
    return True


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Bosch Thermostat Platform."""
    pass




class BoschBaseSwitch(SwitchEntity):
    """Representation of a Bosch charge."""

    def __init__(self, hass, uuid, bosch_object, gateway, name, attr_uri, domain_name, circuit_type=None, is_enabled=False):
        """Set up device and add update callback to get data from websocket."""
        self.hass = hass
        self._bosch_object = bosch_object
        self._gateway = gateway
        self._domain_name = domain_name
        self._name = name
        self._attr_uri = attr_uri
        self._state = bosch_object.state
        self._update_init = True
        self._unit_of_measurement = None
        self._uuid = uuid
        self._unique_id = self._domain_name + self._name + self._uuid
        self._attrs = {}
        self._circuit_type = circuit_type
        self._is_enabled = is_enabled

    @property
    def device_info(self):
        """Get attributes about the device."""
        return {
            "identifiers": self._domain_identifier,
            "manufacturer": self._gateway.device_model,
            "model": self._gateway.device_type,
            "name": self._sensor_name,
            "sw_version": self._gateway.firmware,
            "via_device": (DOMAIN, self._uuid),
        }

    @property
    def unique_id(self):
        """Return unique ID for this device."""
        return self._unique_id

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.hass.helpers.dispatcher.async_dispatcher_connect(
            SIGNAL_SWITCH, self.async_update
        )

    @property
    def bosch_object(self):
        """Return upstream component. Used for refreshing."""
        return self._bosch_object

    async def async_turn_on(self, **kwargs):
        """Turn on switch."""
        _LOGGER.debug("Turning on %s switch.", self._name)
        await self._bosch_object.turn_on()
        self._state = True
        self.async_write_ha_state()

    async def async_update(self):
        self._state = self._bosch_object.state


    async def async_turn_off(self, **kwargs):
        """Turn off switch."""
        _LOGGER.debug("Turning off %s switch.", self._name)
        await self._bosch_object.turn_off()
        self._state = False
        self.async_write_ha_state()

    @property
    def signal(self):
        return SIGNAL_SWITCH

    @property
    def name(self):
        return self._name

    @property
    def _domain_identifier(self):
        return {(DOMAIN, self._domain_name + self._uuid)}

    @property
    def should_poll(self):
        """Don't poll."""
        return False

    @property
    def entity_registry_enabled_default(self):
        """Return if the entity should be enabled when first added to the entity registry."""
        return self._is_enabled

class BoschSwitch(BoschBaseSwitch):
    """Representation of a Bosch switch."""

    @property
    def _sensor_name(self):
        return "Bosch switches"


class CircuitSwitch(BoschBaseSwitch):
    """Representation of a Bosch circuit switch."""
    @property
    def _sensor_name(self):
        return CIRCUITS_SENSOR_NAMES[self._circuit_type] + " " + self._domain_name

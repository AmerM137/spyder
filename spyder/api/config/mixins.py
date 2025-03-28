# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder API helper mixins.
"""

# Standard library imports
import logging
from typing import Any, Callable, Optional, Union
import warnings

# Third-party imports
from qtpy import PYSIDE6

# Local imports
from spyder.config.manager import CONF
from spyder.config.types import ConfigurationKey
from spyder.config.user import NoDefault


logger = logging.getLogger(__name__)

BasicTypes = Union[bool, int, str, tuple, list, dict]


class SpyderConfigurationAccessor:
    """
    Mixin used to access options stored in the Spyder configuration system.
    """

    # Name of the configuration section that's going to be
    # used to record the object's permanent data in Spyder
    # config system.
    CONF_SECTION = None

    def get_conf(
        self,
        option: ConfigurationKey,
        default: Union[NoDefault, BasicTypes] = NoDefault,
        section: Optional[str] = None,
        secure: Optional[bool] = False,
    ):
        """
        Get an option from the Spyder configuration system.

        Parameters
        ----------
        option: ConfigurationKey
            Name/Tuple path of the option to get its value from.
        default: Union[NoDefault, BasicTypes]
            Fallback value to return if the option is not found on the
            configuration system.
        section: str
            Section in the configuration system, e.g. `shortcuts`. If None,
            then the value of `CONF_SECTION` is used.
        secure: bool
            If True, the option will be retrieved securely using the `keyring`
            Python package.

        Returns
        -------
        value: BasicTypes
            Value of the option in the configuration section.

        Raises
        ------
        configparser.NoOptionError
            If the section does not exist in the configuration.
        """
        section = self.CONF_SECTION if section is None else section
        if section is None:
            raise AttributeError(
                'A SpyderConfigurationAccessor must define a `CONF_SECTION` '
                'class attribute!'
            )

        return CONF.get(section, option, default, secure)

    def get_conf_options(self, section: Optional[str] = None):
        """
        Get all options from the given section.

        Parameters
        ----------
        section: Optional[str]
            Section in the configuration system, e.g. `shortcuts`. If None,
            then the value of `CONF_SECTION` is used.

        Returns
        -------
        values: BasicTypes
            Values of the option in the configuration section.

        Raises
        ------
        configparser.NoOptionError
            If the section does not exist in the configuration.
        """
        section = self.CONF_SECTION if section is None else section
        if section is None:
            raise AttributeError(
                'A SpyderConfigurationAccessor must define a `CONF_SECTION` '
                'class attribute!'
            )
        return CONF.options(section)

    def set_conf(
        self,
        option: ConfigurationKey,
        value: BasicTypes,
        section: Optional[str] = None,
        recursive_notification: bool = True,
        secure: Optional[bool] = False,
    ):
        """
        Set an option in the Spyder configuration system.

        Parameters
        ----------
        option: ConfigurationKey
            Name/Tuple path of the option to set its value.
        value: BasicTypes
            Value to set on the configuration system.
        section: Optional[str]
            Section in the configuration system, e.g. `shortcuts`. If None,
            then the value of `CONF_SECTION` is used.
        recursive_notification: bool
            If True, all objects that observe all changes on the
            configuration section and objects that observe partial tuple paths
            are notified. For example if the option `opt` of section `sec`
            changes, then the observers for section `sec` are notified.
            Likewise, if the option `(a, b, c)` changes, then observers for
            `(a, b, c)`, `(a, b)` and a are notified as well.
        secure: bool
            If True, the option will be saved securely using the `keyring`
            Python package.
        """
        section = self.CONF_SECTION if section is None else section
        if section is None:
            raise AttributeError(
                'A SpyderConfigurationAccessor must define a `CONF_SECTION` '
                'class attribute!'
            )
        CONF.set(
            section,
            option,
            value,
            recursive_notification=recursive_notification,
            secure=secure,
        )

    def remove_conf(
        self,
        option: ConfigurationKey,
        section: Optional[str] = None,
        secure: Optional[str] = False,
    ):
        """
        Remove an option in the Spyder configuration system.

        Parameters
        ----------
        option: ConfigurationKey
            Name/Tuple path of the option to remove its value.
        section: Optional[str]
            Section in the configuration system, e.g. `shortcuts`. If None,
            then the value of `CONF_SECTION` is used.
        secure: bool
            If True, the option will be removed securely using the `keyring`
            Python package.
        """
        section = self.CONF_SECTION if section is None else section
        if section is None:
            raise AttributeError(
                'A SpyderConfigurationAccessor must define a `CONF_SECTION` '
                'class attribute!'
            )
        CONF.remove_option(section, option, secure)

    def get_conf_default(self,
                         option: ConfigurationKey,
                         section: Optional[str] = None):
        """
        Get an option default value in the Spyder configuration system.

        Parameters
        ----------
        option: ConfigurationKey
            Name/Tuple path of the option to remove its value.
        section: Optional[str]
            Section in the configuration system, e.g. `shortcuts`. If None,
            then the value of `CONF_SECTION` is used.
        """
        section = self.CONF_SECTION if section is None else section
        if section is None:
            raise AttributeError(
                'A SpyderConfigurationAccessor must define a `CONF_SECTION` '
                'class attribute!'
            )
        return CONF.get_default(section, option)

    @property
    def old_conf_version(self):
        """Get old Spyder configuration version."""
        return CONF.old_spyder_version


class SpyderConfigurationObserver(SpyderConfigurationAccessor):
    """
    Concrete implementation of the protocol
    :class:`spyder.config.types.ConfigurationObserver`.

    This mixin enables a class to receive configuration updates seamlessly,
    by registering methods using the
    :function:`spyder.api.config.decorators.on_conf_change` decorator, which
    receives a configuration section and option to observe.

    When a change occurs on any of the registered configuration options,
    the corresponding registered method is called with the new value.
    """

    def __init__(self):
        super().__init__()
        if self.CONF_SECTION is None:
            warnings.warn(
                'A SpyderConfigurationObserver must define a `CONF_SECTION` '
                f'class attribute! Hint: {self} or its parent should define '
                'the section.'
            )

        self._configuration_listeners = {}
        self._multi_option_listeners = set({})
        self._gather_observers()
        self._merge_none_observers()

        # Register class to listen for changes in all registered options
        for section in self._configuration_listeners:
            section = self.CONF_SECTION if section is None else section
            observed_options = self._configuration_listeners[section]
            for option in observed_options:
                # Avoid a crash at startup due to MRO
                if not PYSIDE6:
                    logger.debug(
                        f'{self} is observing option "{option}" in section '
                        f'"{section}"'
                    )

                CONF.observe_configuration(self, section, option)

    def __del__(self):
        # Remove object from the configuration observer
        CONF.unobserve_configuration(self)

    def _gather_observers(self):
        """Gather all the methods decorated with `on_conf_change`."""
        for method_name in dir(self):
            # Avoid crash at startup due to MRO
            if PYSIDE6 and method_name in {
                # PySide seems to require that the class is instantiated to
                # access this method
                "painters",
                # Method is debounced
                "restart_kernel",
            }:
                continue

            method = getattr(self, method_name, None)
            if hasattr(method, '_conf_listen'):
                info = method._conf_listen
                if len(info) > 1:
                    self._multi_option_listeners |= {method_name}

                for section, option in info:
                    self._add_listener(method_name, option, section)

    def _merge_none_observers(self):
        """Replace observers that declared section as None by CONF_SECTION."""
        default_selectors = self._configuration_listeners.get(None, {})
        section_selectors = self._configuration_listeners.get(
            self.CONF_SECTION, {})

        for option in default_selectors:
            default_option_receivers = default_selectors.get(option, [])
            section_option_receivers = section_selectors.get(option, [])
            merged_receivers = (
                default_option_receivers + section_option_receivers)
            section_selectors[option] = merged_receivers

        self._configuration_listeners[self.CONF_SECTION] = section_selectors
        self._configuration_listeners.pop(None, None)

    def _add_listener(
        self, func: Callable, option: ConfigurationKey, section: str
    ):
        """
        Add a callable as listener of the option `option` on section `section`.

        Parameters
        ----------
        func: Callable
            Function/method that will be called when `option` changes.
        option: ConfigurationKey
            Configuration option to observe.
        section: str
            Name of the section where `option` is contained.
        """
        section_listeners = self._configuration_listeners.get(section, {})
        option_listeners = section_listeners.get(option, [])
        option_listeners.append(func)
        section_listeners[option] = option_listeners
        self._configuration_listeners[section] = section_listeners

    def on_configuration_change(self, option: ConfigurationKey, section: str,
                                value: Any):
        """
        Handle configuration updates for the option `option` on the section
        `section`, whose new value corresponds to `value`.

        Parameters
        ----------
        option: ConfigurationKey
            Configuration option that did change.
        section: str
            Name of the section where `option` is contained.
        value: Any
            New value of the configuration option that produced the event.
        """
        section_receivers = self._configuration_listeners.get(section, {})
        option_receivers = section_receivers.get(option, [])
        for receiver in option_receivers:
            method = (
                receiver if callable(receiver) else getattr(self, receiver)
            )
            if receiver in self._multi_option_listeners:
                method(option, value)
            else:
                method(value)

    def add_configuration_observer(
        self, func: Callable, option: str, section: Optional[str] = None
    ):
        """
        Add a callable to observe the option `option` on section `section`.

        Parameters
        ----------
        func: Callable
            Function that will be called when `option` changes.
        option: ConfigurationKey
            Configuration option to observe.
        section: str
            Name of the section where `option` is contained.

        Notes
        -----
        - This is only necessary if you need to add a callable that is not a
          class method to observe an option. Otherwise, you simply need to
          decorate your method with
          :function:`spyder.api.config.decorators.on_conf_change`.
        """
        if section is None:
            section = self.CONF_SECTION

        logger.debug(
            f'{self} is observing "{option}" option on section "{section}"'
        )
        self._add_listener(func, option, section)
        CONF.observe_configuration(self, section, option)

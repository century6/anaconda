#
# Kickstart module for packaging.
#
# Copyright (C) 2018 Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#
from pyanaconda.core.dbus import DBus
from pyanaconda.core.signal import Signal
from pyanaconda.modules.common.base import KickstartService
from pyanaconda.modules.common.constants.services import PAYLOADS
from pyanaconda.modules.common.containers import TaskContainer
from pyanaconda.modules.payloads.constants import PayloadType
from pyanaconda.modules.payloads.source.factory import SourceFactory
from pyanaconda.modules.payloads.payload.factory import PayloadFactory
from pyanaconda.modules.payloads.kickstart import PayloadKickstartSpecification
from pyanaconda.modules.payloads.packages.packages import PackagesModule
from pyanaconda.modules.payloads.payloads_interface import PayloadsInterface

from pyanaconda.anaconda_loggers import get_module_logger
log = get_module_logger(__name__)


class PayloadsService(KickstartService):
    """The Payload service."""

    def __init__(self):
        super().__init__()
        self._created_payloads = []
        self.created_payloads_changed = Signal()

        self._active_payload = None
        self.active_payload_changed = Signal()

        self._packages = PackagesModule()

    def publish(self):
        """Publish the module."""
        TaskContainer.set_namespace(PAYLOADS.namespace)

        self._packages.publish()

        DBus.publish_object(PAYLOADS.object_path, PayloadsInterface(self))
        DBus.register_service(PAYLOADS.service_name)

    @property
    def kickstart_specification(self):
        """Return the kickstart specification."""
        return PayloadKickstartSpecification

    @property
    def created_payloads(self):
        """List of all created payload modules."""
        return self._created_payloads

    def _add_created_payload(self, module):
        """Add a created payload module."""
        self._created_payloads.append(module)
        self.created_payloads_changed.emit(module)
        log.debug("Created the payload %s.", module.type)

    @property
    def active_payload(self):
        """The active payload.

        Payloads are handling the installation process.

        FIXME: Replace this solution by something extensible for multiple payload support.
               Could it be SetPayloads() and using this list to set order of payload installation?

        There are a few types of payloads e.g.: DNF, LiveImage...

        :return: a payload module or None
        """
        return self._active_payload

    def activate_payload(self, payload):
        """Activate the payload."""
        self._active_payload = payload
        self.active_payload_changed.emit()
        log.debug("Activated the payload %s.", payload.type)

    def process_kickstart(self, data):
        """Process the kickstart data."""
        # Create a new payload module.
        payload_type = PayloadFactory.get_type_for_kickstart(data)

        if payload_type:
            payload_module = self.create_payload(payload_type)
            payload_module.process_kickstart(data)
            self.activate_payload(payload_module)

    def setup_kickstart(self, data):
        """Set up the kickstart data."""
        if self.active_payload:
            self.active_payload.setup_kickstart(data)

    def generate_kickstart(self):
        """Return a kickstart string."""
        # FIXME: This is a temporary workaround for RPM sources.
        if self.active_payload and self.active_payload.type != PayloadType.DNF:
            log.debug("Generating kickstart... (skip)")
            return ""

        return super().generate_kickstart()

    def generate_temporary_kickstart(self):
        """Return the temporary kickstart string."""
        # FIXME: This is a temporary workaround for testing.
        return super().generate_kickstart()

    def create_payload(self, payload_type):
        """Create payload based on the passed type.

        :param payload_type: type of the desirable payload
        :type payload_type: value of the payload.base.constants.PayloadType enum
        """
        payload = PayloadFactory.create_payload(payload_type)
        self._add_created_payload(payload)
        return payload

    def create_source(self, source_type):
        """Create source based on the passed type.

        :param source_type: type of the desirable source
        :type source_type: value of the payload.base.constants.SourceType enum
        """
        return SourceFactory.create_source(source_type)
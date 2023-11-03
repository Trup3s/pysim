# -*- coding: utf-8 -*-

# Copyright (C) 2009-2010  Sylvain Munaut <tnt@246tNt.com>
# Copyright (C) 2010-2023  Harald Welte <laforge@gnumonks.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import argparse
import os
import re
from typing import Optional, Union

from smartcard.CardConnection import CardConnection
from smartcard.CardRequest import CardRequest
from smartcard.Exceptions import NoCardException, CardRequestTimeoutException, CardConnectionException, CardConnectionException
from smartcard.System import readers

from pySim.exceptions import NoCardError, ProtocolError, ReaderError
from pySim.transport import LinkBase
from pySim.utils import h2i, i2h, Hexstr, ResTuple


class PcscSimLink(LinkBase):
    """ pySim: PCSC reader transport link."""

    def __init__(self, opts: argparse.Namespace = argparse.Namespace(pcsc_dev=0), **kwargs):
        super().__init__(**kwargs)
        self._reader = None
        r = readers()
        if opts.pcsc_dev is not None:
            # actual reader index number (integer)
            reader_number = opts.pcsc_dev
            if reader_number >= len(r):
                raise ReaderError('No reader found for number %d' % reader_number)
            self._reader = r[reader_number]
        else:
            # reader regex string
            cre = re.compile(opts.pcsc_regex)
            for reader in r:
                if cre.search(reader.name):
                    self._reader = reader
                    break
            if not self._reader:
                raise ReaderError('No matching reader found for regex %s' % opts.pcsc_regex)

        self._con = self._reader.createConnection()

        if os.environ.get('PYSIM_INTEGRATION_TEST') == "1":
            print("Using PC/SC reader interface")
        else:
            print("Using PC/SC reader %s" % self)

    def __del__(self):
        try:
            # FIXME: this causes multiple warnings in Python 3.5.3
            self._con.disconnect()
        except:
            pass
        return

    def wait_for_card(self, timeout: Optional[int] = None, newcardonly: bool = False):
        cr = CardRequest(readers=[self._reader],
                         timeout=timeout, newcardonly=newcardonly)
        try:
            cr.waitforcard()
        except CardRequestTimeoutException:
            raise NoCardError()
        self.connect()

    def connect(self):
        try:
            # To avoid leakage of resources, make sure the reader
            # is disconnected
            self.disconnect()

            # Explicitly select T=0 communication protocol
            self._con.connect(CardConnection.T0_protocol)
        except CardConnectionException:
            raise ProtocolError()
        except NoCardException:
            raise NoCardError()

    def get_atr(self) -> Hexstr:
        return self._con.getATR()

    def disconnect(self):
        self._con.disconnect()

    def reset_card(self):
        self.disconnect()
        self.connect()
        return 1

    def _send_apdu_raw(self, pdu: Hexstr) -> ResTuple:

        apdu = h2i(pdu)

        data, sw1, sw2 = self._con.transmit(apdu)

        sw = [sw1, sw2]

        # Return value
        return i2h(data), i2h(sw)

    def __str__(self) -> str:
        return "PCSC[%s]" % (self._reader)

    @staticmethod
    def argparse_add_reader_args(arg_parser: argparse.ArgumentParser):
        pcsc_group = arg_parser.add_argument_group('PC/SC Reader')
        dev_group = pcsc_group.add_mutually_exclusive_group()
        dev_group.add_argument('-p', '--pcsc-device', type=int, dest='pcsc_dev', metavar='PCSC', default=None,
                               help='Number of PC/SC reader to use for SIM access')
        dev_group.add_argument('--pcsc-regex', type=str, dest='pcsc_regex', metavar='REGEX', default=None,
                               help='Regex matching PC/SC reader to use for SIM access')

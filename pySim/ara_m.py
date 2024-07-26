# -*- coding: utf-8 -*-

# without this, pylint will fail when inner classes are used
# within the 'nested' kwarg of our TlvMeta metaclass on python 3.7 :(
# pylint: disable=undefined-variable

"""
Support for the Secure Element Access Control, specifically the ARA-M inside an UICC.
"""

#
# Copyright (C) 2021 Harald Welte <laforge@osmocom.org>
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


from construct import GreedyBytes, GreedyString, Struct, Enum, Int8ub, Int16ub
from construct import Optional as COptional
from pySim.construct import *
from pySim.filesystem import *
from pySim.tlv import *
from pySim.utils import Hexstr
import pySim.global_platform

# various BER-TLV encoded Data Objects (DOs)


class AidRefDO(BER_TLV_IE, tag=0x4f):
    # SEID v1.1 Table 6-3
    _construct = HexAdapter(GreedyBytes)


class AidRefEmptyDO(BER_TLV_IE, tag=0xc0):
    # SEID v1.1 Table 6-3
    pass


class DevAppIdRefDO(BER_TLV_IE, tag=0xc1):
    # SEID v1.1 Table 6-4
    _construct = HexAdapter(GreedyBytes)


class PkgRefDO(BER_TLV_IE, tag=0xca):
    # Android UICC Carrier Privileges specific extension, see https://source.android.com/devices/tech/config/uicc
    _construct = Struct('package_name_string'/GreedyString("ascii"))


class RefDO(BER_TLV_IE, tag=0xe1, nested=[AidRefDO, AidRefEmptyDO, DevAppIdRefDO, PkgRefDO]):
    # SEID v1.1 Table 6-5
    pass


class ApduArDO(BER_TLV_IE, tag=0xd0):
    # SEID v1.1 Table 6-8
    def _from_bytes(self, do: bytes):
        if len(do) == 1:
            if do[0] == 0x00:
                self.decoded = {'generic_access_rule': 'never'}
                return self.decoded
            if do[0] == 0x01:
                self.decoded = {'generic_access_rule': 'always'}
                return self.decoded
            return ValueError('Invalid 1-byte generic APDU access rule')
        else:
            if len(do) % 8:
                return ValueError('Invalid non-modulo-8 length of APDU filter: %d' % len(do))
            self.decoded['apdu_filter'] = []
            offset = 0
            while offset < len(do):
                self.decoded['apdu_filter'] += {'header': b2h(do[offset:offset+4]),
                                                'mask': b2h(do[offset+4:offset+8])}
            self.decoded = res
            return res

    def _to_bytes(self):
        if 'generic_access_rule' in self.decoded:
            if self.decoded['generic_access_rule'] == 'never':
                return b'\x00'
            if self.decoded['generic_access_rule'] == 'always':
                return b'\x01'
            return ValueError('Invalid 1-byte generic APDU access rule')
        else:
            if not 'apdu_filter' in self.decoded:
                return ValueError('Invalid APDU AR DO')
            filters = self.decoded['apdu_filter']
            res = b''
            for f in filters:
                if not 'header' in f or not 'mask' in f:
                    return ValueError('APDU filter must contain header and mask')
                header_b = h2b(f['header'])
                mask_b = h2b(f['mask'])
                if len(header_b) != 4 or len(mask_b) != 4:
                    return ValueError('APDU filter header and mask must each be 4 bytes')
                res += header_b + mask_b
            return res


class NfcArDO(BER_TLV_IE, tag=0xd1):
    # SEID v1.1 Table 6-9
    _construct = Struct('nfc_event_access_rule' /
                        Enum(Int8ub, never=0, always=1))


class PermArDO(BER_TLV_IE, tag=0xdb):
    # Android UICC Carrier Privileges specific extension, see https://source.android.com/devices/tech/config/uicc
    # based on Table 6-8 of GlobalPlatform Device API Access Control v1.0
    _construct = Struct('permissions'/HexAdapter(Bytes(8)))


class ArDO(BER_TLV_IE, tag=0xe3, nested=[ApduArDO, NfcArDO, PermArDO]):
    # SEID v1.1 Table 6-7
    pass


class RefArDO(BER_TLV_IE, tag=0xe2, nested=[RefDO, ArDO]):
    # SEID v1.1 Table 6-6
    pass


class ResponseAllRefArDO(BER_TLV_IE, tag=0xff40, nested=[RefArDO]):
    # SEID v1.1 Table 4-2
    pass


class ResponseArDO(BER_TLV_IE, tag=0xff50, nested=[ArDO]):
    # SEID v1.1 Table 4-3
    pass


class ResponseRefreshTagDO(BER_TLV_IE, tag=0xdf20):
    # SEID v1.1 Table 4-4
    _construct = Struct('refresh_tag'/HexAdapter(Bytes(8)))


class DeviceInterfaceVersionDO(BER_TLV_IE, tag=0xe6):
    # SEID v1.1 Table 6-12
    _construct = Struct('major'/Int8ub, 'minor'/Int8ub, 'patch'/Int8ub)


class DeviceConfigDO(BER_TLV_IE, tag=0xe4, nested=[DeviceInterfaceVersionDO]):
    # SEID v1.1 Table 6-10
    pass


class ResponseDeviceConfigDO(BER_TLV_IE, tag=0xff7f, nested=[DeviceConfigDO]):
    # SEID v1.1 Table 5-14
    pass


class AramConfigDO(BER_TLV_IE, tag=0xe5, nested=[DeviceInterfaceVersionDO]):
    # SEID v1.1 Table 6-11
    pass


class ResponseAramConfigDO(BER_TLV_IE, tag=0xdf21, nested=[AramConfigDO]):
    # SEID v1.1 Table 4-5
    pass


class CommandStoreRefArDO(BER_TLV_IE, tag=0xf0, nested=[RefArDO]):
    # SEID v1.1 Table 5-2
    pass


class CommandDelete(BER_TLV_IE, tag=0xf1, nested=[AidRefDO, AidRefEmptyDO, RefDO, RefArDO]):
    # SEID v1.1 Table 5-4
    pass


class CommandUpdateRefreshTagDO(BER_TLV_IE, tag=0xf2):
    # SEID V1.1 Table 5-6
    pass


class CommandRegisterClientAidsDO(BER_TLV_IE, tag=0xf7, nested=[AidRefDO, AidRefEmptyDO]):
    # SEID v1.1 Table 5-7
    pass


class CommandGet(BER_TLV_IE, tag=0xf3, nested=[AidRefDO, AidRefEmptyDO]):
    # SEID v1.1 Table 5-8
    pass


class CommandGetAll(BER_TLV_IE, tag=0xf4):
    # SEID v1.1 Table 5-9
    pass


class CommandGetClientAidsDO(BER_TLV_IE, tag=0xf6):
    # SEID v1.1 Table 5-10
    pass


class CommandGetNext(BER_TLV_IE, tag=0xf5):
    # SEID v1.1 Table 5-11
    pass


class CommandGetDeviceConfigDO(BER_TLV_IE, tag=0xf8):
    # SEID v1.1 Table 5-12
    pass


class ResponseAracAidDO(BER_TLV_IE, tag=0xff70, nested=[AidRefDO, AidRefEmptyDO]):
    # SEID v1.1 Table 5-13
    pass


class BlockDO(BER_TLV_IE, tag=0xe7):
    # SEID v1.1 Table 6-13
    _construct = Struct('offset'/Int16ub, 'length'/Int8ub)


# SEID v1.1 Table 4-1
class GetCommandDoCollection(TLV_IE_Collection, nested=[RefDO, DeviceConfigDO]):
    pass


# SEID v1.1 Table 4-2
class GetResponseDoCollection(TLV_IE_Collection, nested=[ResponseAllRefArDO, ResponseArDO,
                                                         ResponseRefreshTagDO, ResponseAramConfigDO]):
    pass


# SEID v1.1 Table 5-1
class StoreCommandDoCollection(TLV_IE_Collection,
                               nested=[BlockDO, CommandStoreRefArDO, CommandDelete,
                                       CommandUpdateRefreshTagDO, CommandRegisterClientAidsDO,
                                       CommandGet, CommandGetAll, CommandGetClientAidsDO,
                                       CommandGetNext, CommandGetDeviceConfigDO]):
    pass


# SEID v1.1 Section 5.1.2
class StoreResponseDoCollection(TLV_IE_Collection,
                                nested=[ResponseAllRefArDO, ResponseAracAidDO, ResponseDeviceConfigDO]):
    pass


class ADF_ARAM(CardADF):
    def __init__(self, aid='a00000015141434c00', name='ADF.ARA-M', fid=None, sfid=None,
                 desc='ARA-M Application'):
        super().__init__(aid=aid, fid=fid, sfid=sfid, name=name, desc=desc)
        self.shell_commands += [self.AddlShellCommands()]
        files = []
        self.add_files(files)

    def decode_select_response(self, data_hex):
        return pySim.global_platform.decode_select_response(data_hex)

    @staticmethod
    def xceive_apdu_tlv(tp, hdr: Hexstr, cmd_do, resp_cls, exp_sw='9000'):
        """Transceive an APDU with the card, transparently encoding the command data from TLV
        and decoding the response data tlv."""
        if cmd_do:
            cmd_do_enc = cmd_do.to_ie()
            cmd_do_len = len(cmd_do_enc)
            if cmd_do_len > 255:
                return ValueError('DO > 255 bytes not supported yet')
        else:
            cmd_do_enc = b''
            cmd_do_len = 0
        c_apdu = hdr + ('%02x' % cmd_do_len) + b2h(cmd_do_enc)
        (data, _sw) = tp.send_apdu_checksw(c_apdu, exp_sw)
        if data:
            if resp_cls:
                resp_do = resp_cls()
                resp_do.from_tlv(h2b(data))
                return resp_do
            return data
        else:
            return None

    @staticmethod
    def store_data(tp, do) -> bytes:
        """Build the Command APDU for STORE DATA."""
        return ADF_ARAM.xceive_apdu_tlv(tp, '80e29000', do, StoreResponseDoCollection)

    @staticmethod
    def get_all(tp):
        return ADF_ARAM.xceive_apdu_tlv(tp, '80caff40', None, GetResponseDoCollection)

    @staticmethod
    def get_config(tp, v_major=0, v_minor=0, v_patch=1):
        cmd_do = DeviceConfigDO()
        cmd_do.from_dict([{'device_interface_version_do': {
                         'major': v_major, 'minor': v_minor, 'patch': v_patch}}])
        return ADF_ARAM.xceive_apdu_tlv(tp, '80cadf21', cmd_do, ResponseAramConfigDO)

    @with_default_category('Application-Specific Commands')
    class AddlShellCommands(CommandSet):
        def do_aram_get_all(self, _opts):
            """GET DATA [All] on the ARA-M Applet"""
            res_do = ADF_ARAM.get_all(self._cmd.lchan.scc._tp)
            if res_do:
                self._cmd.poutput_json(res_do.to_dict())

        def do_aram_get_config(self, _opts):
            """Perform GET DATA [Config] on the ARA-M Applet: Tell it our version and retrieve its version."""
            res_do = ADF_ARAM.get_config(self._cmd.lchan.scc._tp)
            if res_do:
                self._cmd.poutput_json(res_do.to_dict())

        store_ref_ar_do_parse = argparse.ArgumentParser()
        # REF-DO
        store_ref_ar_do_parse.add_argument(
            '--device-app-id', required=True, help='Identifies the specific device application that the rule appplies to. Hash of Certificate of Application Provider, or UUID. (20/32 hex bytes)')
        aid_grp = store_ref_ar_do_parse.add_mutually_exclusive_group()
        aid_grp.add_argument(
            '--aid', help='Identifies the specific SE application for which rules are to be stored. Can be a partial AID, containing for example only the RID.  (5-16 hex bytes)')
        aid_grp.add_argument('--aid-empty', action='store_true',
                             help='No specific SE application, applies to all applications')
        store_ref_ar_do_parse.add_argument(
            '--pkg-ref', help='Full Android Java package name (up to 127 chars ASCII)')
        # AR-DO
        apdu_grp = store_ref_ar_do_parse.add_mutually_exclusive_group()
        apdu_grp.add_argument(
            '--apdu-never', action='store_true', help='APDU access is not allowed')
        apdu_grp.add_argument(
            '--apdu-always', action='store_true', help='APDU access is allowed')
        apdu_grp.add_argument(
            '--apdu-filter', help='APDU filter: 4 byte CLA/INS/P1/P2 followed by 4 byte mask (8 hex bytes)')
        nfc_grp = store_ref_ar_do_parse.add_mutually_exclusive_group()
        nfc_grp.add_argument('--nfc-always', action='store_true',
                             help='NFC event access is allowed')
        nfc_grp.add_argument('--nfc-never', action='store_true',
                             help='NFC event access is not allowed')
        store_ref_ar_do_parse.add_argument(
            '--android-permissions', help='Android UICC Carrier Privilege Permissions (8 hex bytes)')

        @cmd2.with_argparser(store_ref_ar_do_parse)
        def do_aram_store_ref_ar_do(self, opts):
            """Perform STORE DATA [Command-Store-REF-AR-DO] to store a (new) access rule."""
            # REF
            ref_do_content = []
            if opts.aid is not None:
                ref_do_content += [{'aid_ref_do': opts.aid}]
            elif opts.aid_empty:
                ref_do_content += [{'aid_ref_empty_do': None}]
            ref_do_content += [{'dev_app_id_ref_do': opts.device_app_id}]
            if opts.pkg_ref:
                ref_do_content += [{'pkg_ref_do': {'package_name_string': opts.pkg_ref}}]
            # AR
            ar_do_content = []
            if opts.apdu_never:
                ar_do_content += [{'apdu_ar_od': {'generic_access_rule': 'never'}}]
            elif opts.apdu_always:
                ar_do_content += [{'apdu_ar_do': {'generic_access_rule': 'always'}}]
            elif opts.apdu_filter:
                # TODO: multiple filters
                ar_do_content += [{'apdu_ar_do': {'apdu_filter': [opts.apdu_filter]}}]
            if opts.nfc_always:
                ar_do_content += [{'nfc_ar_do': {'nfc_event_access_rule': 'always'}}]
            elif opts.nfc_never:
                ar_do_content += [{'nfc_ar_do': {'nfc_event_access_rule': 'never'}}]
            if opts.android_permissions:
                ar_do_content += [{'perm_ar_do': {'permissions': opts.android_permissions}}]
            d = [{'ref_ar_do': [{'ref_do': ref_do_content}, {'ar_do': ar_do_content}]}]
            csrado = CommandStoreRefArDO()
            csrado.from_dict(d)
            res_do = ADF_ARAM.store_data(self._cmd.lchan.scc._tp, csrado)
            if res_do:
                self._cmd.poutput_json(res_do.to_dict())

        def do_aram_delete_all(self, _opts):
            """Perform STORE DATA [Command-Delete[all]] to delete all access rules."""
            deldo = CommandDelete()
            res_do = ADF_ARAM.store_data(self._cmd.lchan.scc._tp, deldo)
            if res_do:
                self._cmd.poutput_json(res_do.to_dict())


# SEAC v1.1 Section 4.1.2.2 + 5.1.2.2
sw_aram = {
    'ARA-M': {
        '6381': 'Rule successfully stored but an access rule already exists',
        '6382': 'Rule successfully stored bu contained at least one unknown (discarded) BER-TLV',
        '6581': 'Memory Problem',
        '6700': 'Wrong Length in Lc',
        '6981': 'DO is not supported by the ARA-M/ARA-C',
        '6982': 'Security status not satisfied',
        '6984': 'Rules have been updated and must be read again / logical channels in use',
        '6985': 'Conditions not satisfied',
        '6a80': 'Incorrect values in the command data',
        '6a84': 'Rules have been updated and must be read again',
        '6a86': 'Incorrect P1 P2',
        '6a88': 'Referenced data not found',
        '6a89': 'Conflicting access rule already exists in the Secure Element',
        '6d00': 'Invalid instruction',
        '6e00': 'Invalid class',
    }
}


class CardApplicationARAM(CardApplication):
    def __init__(self):
        super().__init__('ARA-M', adf=ADF_ARAM(), sw=sw_aram)

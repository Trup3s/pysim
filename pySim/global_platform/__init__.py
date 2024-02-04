# coding=utf-8
"""Partial Support for GlobalPLatform Card Spec (currently 2.1.1)

(C) 2022-2024 by Harald Welte <laforge@osmocom.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from construct import Optional as COptional
from construct import Struct, GreedyRange, FlagsEnum, Int16ub, Padding, Bit, Const
from typing import Optional, List, Dict, Tuple
from copy import deepcopy
from bidict import bidict
from Cryptodome.Random import get_random_bytes
from pySim.global_platform.scp import SCP02, SCP03
from pySim.construct import *
from pySim.utils import *
from pySim.filesystem import *
from pySim.tlv import *
from pySim.profile import CardProfile

sw_table = {
    'Warnings': {
        '6200': 'Logical Channel already closed',
        '6283': 'Card Life Cycle State is CARD_LOCKED',
        '6310': 'More data available',
    },
    'Execution errors': {
        '6400': 'No specific diagnosis',
        '6581': 'Memory failure',
    },
    'Checking errors': {
        '6700': 'Wrong length in Lc',
    },
    'Functions in CLA not supported': {
        '6881': 'Logical channel not supported or active',
        '6882': 'Secure messaging not supported',
    },
    'Command not allowed': {
        '6982': 'Security Status not satisfied',
        '6985': 'Conditions of use not satisfied',
    },
    'Wrong parameters': {
        '6a80': 'Incorrect values in command data',
        '6a81': 'Function not supported e.g. card Life Cycle State is CARD_LOCKED',
        '6a82': 'Application not found',
        '6a84': 'Not enough memory space',
        '6a86': 'Incorrect P1 P2',
        '6a88': 'Referenced data not found',
    },
    'GlobalPlatform': {
        '6d00': 'Invalid instruction',
        '6e00': 'Invalid class',
    },
    'Application errors': {
        '9484': 'Algorithm not supported',
        '9485': 'Invalid key check value',
    },
}

# GlobalPlatform 2.1.1 Section 9.1.6
KeyType = Enum(Byte,    des=0x80,
                        tls_psk=0x85,                           # v2.3.1 Section 11.1.8
                        aes=0x88,                               # v2.3.1 Section 11.1.8
                        hmac_sha1=0x90,                         # v2.3.1 Section 11.1.8
                        hmac_sha1_160=0x91,                     # v2.3.1 Section 11.1.8
                        rsa_public_exponent_e_cleartex=0xA0,
                        rsa_modulus_n_cleartext=0xA1,
                        rsa_modulus_n=0xA2,
                        rsa_private_exponent_d=0xA3,
                        rsa_chines_remainder_p=0xA4,
                        rsa_chines_remainder_q=0xA5,
                        rsa_chines_remainder_pq=0xA6,
                        rsa_chines_remainder_dpi=0xA7,
                        rsa_chines_remainder_dqi=0xA8,
                        ecc_public_key=0xB0,                    # v2.3.1 Section 11.1.8
                        ecc_private_key=0xB1,                   # v2.3.1 Section 11.1.8
                        ecc_field_parameter_p=0xB2,             # v2.3.1 Section 11.1.8
                        ecc_field_parameter_a=0xB3,             # v2.3.1 Section 11.1.8
                        ecc_field_parameter_b=0xB4,             # v2.3.1 Section 11.1.8
                        ecc_field_parameter_g=0xB5,             # v2.3.1 Section 11.1.8
                        ecc_field_parameter_n=0xB6,             # v2.3.1 Section 11.1.8
                        ecc_field_parameter_k=0xB7,             # v2.3.1 Section 11.1.8
                        ecc_key_parameters_reference=0xF0,      # v2.3.1 Section 11.1.8
                        not_available=0xff)

# GlobalPlatform 2.3 Section 11.10.2.1 Table 11-86
SetStatusScope = Enum(Byte, isd=0x80, app_or_ssd=0x40, isd_and_assoc_apps=0xc0)

# GlobalPlatform 2.3 section 11.1.1
CLifeCycleState = Enum(Byte, loaded=0x01, installed=0x03, selectable=0x07, personalized=0x0f, locked=0x83)

# GlobalPlatform 2.1.1 Section 9.3.3.1
class KeyInformationData(BER_TLV_IE, tag=0xc0):
    _test_de_encode = [
        ( 'c00401708010', {"key_identifier": 1, "key_version_number": 112, "key_types": [ {"length": 16, "type": "des"} ]} ),
        ( 'c00402708010', {"key_identifier": 2, "key_version_number": 112, "key_types": [ {"length": 16, "type": "des"} ]} ),
        ( 'c00403708010', {"key_identifier": 3, "key_version_number": 112, "key_types": [ {"length": 16, "type": "des"} ]} ),
        ( 'c00401018010', {"key_identifier": 1, "key_version_number": 1, "key_types": [ {"length": 16, "type": "des"} ]} ),
        ( 'c00402018010', {"key_identifier": 2, "key_version_number": 1, "key_types": [ {"length": 16, "type": "des"} ]} ),
        ( 'c00403018010', {"key_identifier": 3, "key_version_number": 1, "key_types": [ {"length": 16, "type": "des"} ]} ),
        ( 'c00401028010', {"key_identifier": 1, "key_version_number": 2, "key_types": [ {"length": 16, "type": "des"} ]} ),
        ( 'c00402028010', {"key_identifier": 2, "key_version_number": 2, "key_types": [ {"length": 16, "type": "des"} ]} ),
        ( 'c00403038010', {"key_identifier": 3, "key_version_number": 3, "key_types": [ {"length": 16, "type": "des"} ]} ),
        ( 'c00401038010', {"key_identifier": 1, "key_version_number": 3, "key_types": [ {"length": 16, "type": "des"} ]} ),
        ( 'c00402038010', {"key_identifier": 2, "key_version_number": 3, "key_types": [ {"length": 16, "type": "des"} ]} ),
        ( 'c00402038810', {"key_identifier": 2, "key_version_number": 3, "key_types": [ {"length": 16, "type": "aes"} ]} ),
    ]
    KeyTypeLen = Struct('type'/KeyType, 'length'/Int8ub)
    _construct = Struct('key_identifier'/Byte, 'key_version_number'/Byte,
                        'key_types'/GreedyRange(KeyTypeLen))
class KeyInformation(BER_TLV_IE, tag=0xe0, nested=[KeyInformationData]):
    pass

# GP v2.3 11.1.9
KeyUsageQualifier = Struct('byte1'/FlagsEnum(Byte, verification_encryption=0x80,
                                             computation_decipherment=0x40,
                                             sm_response=0x20,
                                             sm_command=0x10,
                                             confidentiality=0x08,
                                             crypto_checksum=0x04,
                                             digital_signature=0x02,
                                             crypto_authorization=0x01),
                           'byte2'/COptional(FlagsEnum(Byte, key_agreement=0x80)))

# GP v2.3 11.1.10
KeyAccess = Enum(Byte, sd_and_any_assoc_app=0x00, sd_only=0x01, any_assoc_app_but_not_sd=0x02,
                 not_available=0xff)

class KeyLoading:
    # Global Platform Specification v2.3 Section 11.11.4.2.2.3 DGIs for the CC Private Key

    class KeyUsageQualifier(BER_TLV_IE, tag=0x95):
        _construct = KeyUsageQualifier

    class KeyAccess(BER_TLV_IE, tag=0x96):
        _construct = KeyAccess

    class KeyType(BER_TLV_IE, tag=0x80):
        _construct = KeyType

    class KeyLength(BER_TLV_IE, tag=0x81):
        _construct = GreedyInteger()

    class KeyIdentifier(BER_TLV_IE, tag=0x82):
        _construct = Int8ub

    class KeyVersionNumber(BER_TLV_IE, tag=0x83):
        _construct = Int8ub

    class KeyParameterReferenceValue(BER_TLV_IE, tag=0x85):
        _construct = Enum(Byte, secp256r1=0x00, secp384r1=0x01, secp521r1=0x02, brainpoolP256r1=0x03,
                          brainpoolP256t1=0x04, brainpoolP384r1=0x05, brainpoolP384t1=0x06,
                          brainpoolP512r1=0x07, brainpoolP512t1=0x08)

    # pylint: disable=undefined-variable
    class ControlReferenceTemplate(BER_TLV_IE, tag=0xb9,
                                   nested=[KeyUsageQualifier,
                                           KeyAccess,
                                           KeyType,
                                           KeyLength,
                                           KeyIdentifier,
                                           KeyVersionNumber,
                                           KeyParameterReferenceValue]):
        pass

    # Table 11-103
    class EccPublicKey(DGI_TLV_IE, tag=0x0036):
        _construct = GreedyBytes

    # Table 11-105
    class EccPrivateKey(DGI_TLV_IE, tag=0x8137):
        _construct = GreedyBytes

    # Global Platform Specification v2.3 Section 11.11.4 / Table 11-91
    class KeyControlReferenceTemplate(DGI_TLV_IE, tag=0x00b9, nested=[ControlReferenceTemplate]):
        pass


# GlobalPlatform v2.3.1 Section H.4 / Table H-6
class ScpType(BER_TLV_IE, tag=0x80):
    _construct = HexAdapter(Byte)
class ListOfSupportedOptions(BER_TLV_IE, tag=0x81):
    _construct = GreedyBytes
class SupportedKeysForScp03(BER_TLV_IE, tag=0x82):
    _construct = FlagsEnum(Byte, aes128=0x01, aes192=0x02, aes256=0x04)
class SupportedTlsCipherSuitesForScp81(BER_TLV_IE, tag=0x83):
    _consuruct = GreedyRange(Int16ub)
class ScpInformation(BER_TLV_IE, tag=0xa0, nested=[ScpType, ListOfSupportedOptions, SupportedKeysForScp03,
                                                   SupportedTlsCipherSuitesForScp81]):
    pass
class PrivilegesAvailableSSD(BER_TLV_IE, tag=0x81):
    pass
class PrivilegesAvailableApplication(BER_TLV_IE, tag=0x82):
    pass
class SupportedLFDBHAlgorithms(BER_TLV_IE, tag=0x83):
    pass
# GlobalPlatform Card Specification v2.3 / Table H-8
class CiphersForLFDBEncryption(BER_TLV_IE, tag=0x84):
    _construct = Enum(Byte, tripledes16=0x01, aes128=0x02, aes192=0x04, aes256=0x08,
                      icv_supported_for_lfdb=0x80)
CipherSuitesForSignatures = Struct('byte1'/FlagsEnum(Byte, rsa1024_pkcsv15_sha1=0x01,
                                                     rsa_gt1024_pss_sha256=0x02,
                                                     single_des_plus_final_triple_des_mac_16b=0x04,
                                                     cmac_aes128=0x08, cmac_aes192=0x10, cmac_aes256=0x20,
                                                     ecdsa_ecc256_sha256=0x40, ecdsa_ecc384_sha384=0x80),
                                   'byte2'/COptional(FlagsEnum(Byte, ecdsa_ecc512_sha512=0x01,
                                                               ecdsa_ecc_521_sha512=0x02)))
class CiphersForTokens(BER_TLV_IE, tag=0x85):
    _construct = CipherSuitesForSignatures
class CiphersForReceipts(BER_TLV_IE, tag=0x86):
    _construct = CipherSuitesForSignatures
class CiphersForDAPs(BER_TLV_IE, tag=0x87):
    _construct = CipherSuitesForSignatures
class KeyParameterReferenceList(BER_TLV_IE, tag=0x88, nested=[KeyLoading.KeyParameterReferenceValue]):
    pass
class CardCapabilityInformation(BER_TLV_IE, tag=0x67, nested=[ScpInformation, PrivilegesAvailableSSD,
                                                              PrivilegesAvailableApplication,
                                                              SupportedLFDBHAlgorithms,
                                                              CiphersForLFDBEncryption, CiphersForTokens,
                                                              CiphersForReceipts, CiphersForDAPs,
                                                              KeyParameterReferenceList]):
    pass

class CurrentSecurityLevel(BER_TLV_IE, tag=0xd3):
    _construct = Int8ub

# GlobalPlatform v2.3.1 Section 11.3.3.1.3
class ApplicationAID(BER_TLV_IE, tag=0x4f):
    _construct = HexAdapter(GreedyBytes)
class ApplicationTemplate(BER_TLV_IE, tag=0x61, ntested=[ApplicationAID]):
    pass
class ListOfApplications(BER_TLV_IE, tag=0x2f00, nested=[ApplicationTemplate]):
    pass

# GlobalPlatform v2.3.1 Section 11.3.3.1.2 + TS 102 226
class NumberOFInstalledApp(BER_TLV_IE, tag=0x81):
    _construct = GreedyInteger()
class FreeNonVolatileMemory(BER_TLV_IE, tag=0x82):
    _construct = GreedyInteger()
class FreeVolatileMemory(BER_TLV_IE, tag=0x83):
    _construct = GreedyInteger()
class ExtendedCardResourcesInfo(BER_TLV_IE, tag=0xff21, nested=[NumberOFInstalledApp, FreeNonVolatileMemory,
                                                                FreeVolatileMemory]):
    pass

# GlobalPlatform v2.3.1 Section 7.4.2.4 + GP SPDM
class SecurityDomainManagerURL(BER_TLV_IE, tag=0x5f50):
    pass


# card data sample, returned in response to GET DATA (80ca006600):
# 66 31
#    73 2f
#        06 07
#            2a864886fc6b01
#        60 0c
#            06 0a
#                2a864886fc6b02020101
#        63 09
#            06 07
#                2a864886fc6b03
#        64 0b
#            06 09
#                2a864886fc6b040215

# GlobalPlatform 2.1.1 Table F-1
class ObjectIdentifier(BER_TLV_IE, tag=0x06):
    _construct = GreedyBytes
class CardManagementTypeAndVersion(BER_TLV_IE, tag=0x60, nested=[ObjectIdentifier]):
    pass
class CardIdentificationScheme(BER_TLV_IE, tag=0x63, nested=[ObjectIdentifier]):
    pass
class SecureChannelProtocolOfISD(BER_TLV_IE, tag=0x64, nested=[ObjectIdentifier]):
    pass
class CardConfigurationDetails(BER_TLV_IE, tag=0x65):
    _construct = GreedyBytes
class CardChipDetails(BER_TLV_IE, tag=0x66):
    _construct = GreedyBytes
class CardRecognitionData(BER_TLV_IE, tag=0x73, nested=[ObjectIdentifier,
                                                        CardManagementTypeAndVersion,
                                                        CardIdentificationScheme,
                                                        SecureChannelProtocolOfISD,
                                                        CardConfigurationDetails,
                                                        CardChipDetails]):
    pass
class CardData(BER_TLV_IE, tag=0x66, nested=[CardRecognitionData]):
    pass

# GlobalPlatform 2.1.1 Table F-2
class SecureChannelProtocolOfSelectedSD(BER_TLV_IE, tag=0x64, nested=[ObjectIdentifier]):
    pass
class SecurityDomainMgmtData(BER_TLV_IE, tag=0x73, nested=[CardManagementTypeAndVersion,
                                                           CardIdentificationScheme,
                                                           SecureChannelProtocolOfSelectedSD,
                                                           CardConfigurationDetails,
                                                           CardChipDetails]):
    pass

# GlobalPlatform 2.1.1 Section 9.1.1
IsdLifeCycleState = Enum(Byte, op_ready=0x01, initialized=0x07, secured=0x0f,
                         card_locked = 0x7f, terminated=0xff)

# GlobalPlatform 2.1.1 Section 9.9.3.1
class ApplicationID(BER_TLV_IE, tag=0x84):
    _construct = GreedyBytes

# GlobalPlatform 2.1.1 Section 9.9.3.1
class SecurityDomainManagementData(BER_TLV_IE, tag=0x73):
    _construct = GreedyBytes

# GlobalPlatform 2.1.1 Section 9.9.3.1
class ApplicationProductionLifeCycleData(BER_TLV_IE, tag=0x9f6e):
    _construct = GreedyBytes

# GlobalPlatform 2.1.1 Section 9.9.3.1
class MaximumLengthOfDataFieldInCommandMessage(BER_TLV_IE, tag=0x9f65):
    _construct = GreedyInteger()

# GlobalPlatform 2.1.1 Section 9.9.3.1
class ProprietaryData(BER_TLV_IE, tag=0xA5, nested=[SecurityDomainManagementData,
                                                    ApplicationProductionLifeCycleData,
                                                    MaximumLengthOfDataFieldInCommandMessage]):
    pass

# explicitly define this list and give it a name so pySim.euicc can reference it
FciTemplateNestedList = [ApplicationID, SecurityDomainManagementData,
                         ApplicationProductionLifeCycleData,
                         MaximumLengthOfDataFieldInCommandMessage,
                         ProprietaryData]

# GlobalPlatform 2.1.1 Section 9.9.3.1
class FciTemplate(BER_TLV_IE, tag=0x6f, nested=FciTemplateNestedList):
    pass

class IssuerIdentificationNumber(BER_TLV_IE, tag=0x42):
    _construct = HexAdapter(GreedyBytes)

class CardImageNumber(BER_TLV_IE, tag=0x45):
    _construct = HexAdapter(GreedyBytes)

class SequenceCounterOfDefaultKvn(BER_TLV_IE, tag=0xc1):
    _construct = GreedyInteger()

class ConfirmationCounter(BER_TLV_IE, tag=0xc2):
    _construct = GreedyInteger()

# Collection of all the data objects we can get from GET DATA
class DataCollection(TLV_IE_Collection, nested=[IssuerIdentificationNumber,
                                                CardImageNumber,
                                                CardData,
                                                KeyInformation,
                                                SequenceCounterOfDefaultKvn,
                                                ConfirmationCounter,
                                                # v2.3.1
                                                CardCapabilityInformation,
                                                CurrentSecurityLevel,
                                                ListOfApplications,
                                                ExtendedCardResourcesInfo,
                                                SecurityDomainManagerURL]):
    pass

def decode_select_response(resp_hex: str) -> object:
    t = FciTemplate()
    t.from_tlv(h2b(resp_hex))
    d = t.to_dict()
    return flatten_dict_lists(d['fci_template'])

# 11.4.2.1
StatusSubset = Enum(Byte, isd=0x80, applications=0x40, files=0x20, files_and_modules=0x10)


# Section 11.4.3.1 Table 11-36
class LifeCycleState(BER_TLV_IE, tag=0x9f70):
    _construct = CLifeCycleState

# Section 11.4.3.1 Table 11-36 + Section 11.1.2
class Privileges(BER_TLV_IE, tag=0xc5):
    _construct = Struct('byte1'/FlagsEnum(Byte, security_domain=0x80, dap_verification=0x40,
                                          delegated_management=0x20, card_lock=0x10, card_terminate=0x08,
                                          card_reset=0x04, cvm_management=0x02,
                                          mandated_dap_verification=0x01),
                        'byte2'/COptional(FlagsEnum(Byte, trusted_path=0x80, authorized_management=0x40,
                                          token_management=0x20, global_delete=0x10, global_lock=0x08,
                                          global_registry=0x04, final_application=0x02, global_service=0x01)),
                        'byte3'/COptional(FlagsEnum(Byte, receipt_generation=0x80, ciphered_load_file_data_block=0x40,
                                          contactless_activation=0x20, contactless_self_activation=0x10)))

# Section 11.4.3.1 Table 11-36 + Section 11.1.7
class ImplicitSelectionParameter(BER_TLV_IE, tag=0xcf):
    _construct = BitStruct('contactless_io'/Flag,
                           'contact_io'/Flag,
                           '_rfu'/Flag,
                           'logical_channel_number'/BitsInteger(5))

# Section 11.4.3.1 Table 11-36
class ExecutableLoadFileAID(BER_TLV_IE, tag=0xc4):
    _construct = HexAdapter(GreedyBytes)

# Section 11.4.3.1 Table 11-36
class ExecutableLoadFileVersionNumber(BER_TLV_IE, tag=0xce):
    # Note: the Executable Load File Version Number format and contents are beyond the scope of this
    # specification. It shall consist of the version information contained in the original Load File: on a
    # Java Card based card, this version number represents the major and minor version attributes of the
    # original Load File Data Block.
    _construct = HexAdapter(GreedyBytes)

# Section 11.4.3.1 Table 11-36
class ExecutableModuleAID(BER_TLV_IE, tag=0x84):
    _construct = HexAdapter(GreedyBytes)

# Section 11.4.3.1 Table 11-36
class AssociatedSecurityDomainAID(BER_TLV_IE, tag=0xcc):
    _construct = HexAdapter(GreedyBytes)

# Section 11.4.3.1 Table 11-36
class GpRegistryRelatedData(BER_TLV_IE, tag=0xe3, nested=[ApplicationAID, LifeCycleState, Privileges,
                                                          ImplicitSelectionParameter, ExecutableLoadFileAID,
                                                          ExecutableLoadFileVersionNumber,
                                                          ExecutableModuleAID, AssociatedSecurityDomainAID]):
    pass

# Application Dedicated File of a Security Domain
class ADF_SD(CardADF):
    StoreData = BitStruct('last_block'/Flag,
                          'encryption'/Enum(BitsInteger(2), none=0, application_dependent=1, rfu=2, encrypted=3),
                          'structure'/Enum(BitsInteger(2), none=0, dgi=1, ber_tlv=2, rfu=3),
                          '_pad'/Padding(2),
                          'response'/Enum(Bit, not_expected=0, may_be_returned=1))

    def __init__(self, aid: str, name: str, desc: str):
        super().__init__(aid=aid, fid=None, sfid=None, name=name, desc=desc)
        self.shell_commands += [self.AddlShellCommands()]

    @staticmethod
    def decode_select_response(res_hex: str) -> object:
        return decode_select_response(res_hex)

    @with_default_category('Application-Specific Commands')
    class AddlShellCommands(CommandSet):
        def __init__(self):
            super().__init__()

        get_data_parser = argparse.ArgumentParser()
        get_data_parser.add_argument('data_object_name', type=str,
            help='Name of the data object to be retrieved from the card')

        @cmd2.with_argparser(get_data_parser)
        def do_get_data(self, opts):
            """Perform the GlobalPlatform GET DATA command in order to obtain some card-specific data."""
            tlv_cls_name = opts.data_object_name
            try:
                tlv_cls = DataCollection().members_by_name[tlv_cls_name]
            except KeyError:
                do_names = [camel_to_snake(str(x.__name__)) for x in DataCollection.possible_nested]
                self._cmd.poutput('Unknown data object "%s", available options: %s' % (tlv_cls_name,
                                                                                       do_names))
                return
            (data, sw) = self._cmd.lchan.scc.get_data(cla=0x80, tag=tlv_cls.tag)
            ie = tlv_cls()
            ie.from_tlv(h2b(data))
            self._cmd.poutput_json(ie.to_dict())

        def complete_get_data(self, text, line, begidx, endidx) -> List[str]:
            data_dict = {camel_to_snake(str(x.__name__)): x for x in DataCollection.possible_nested}
            index_dict = {1: data_dict}
            return self._cmd.index_based_complete(text, line, begidx, endidx, index_dict=index_dict)

        store_data_parser = argparse.ArgumentParser()
        store_data_parser.add_argument('--data-structure', type=str, choices=['none','dgi','ber_tlv','rfu'], default='none')
        store_data_parser.add_argument('--encryption', type=str, choices=['none','application_dependent', 'rfu', 'encrypted'], default='none')
        store_data_parser.add_argument('--response', type=str, choices=['not_expected','may_be_returned'], default='not_expected')
        store_data_parser.add_argument('DATA', type=is_hexstr)

        @cmd2.with_argparser(store_data_parser)
        def do_store_data(self, opts):
            """Perform the GlobalPlatform GET DATA command in order to store some card-specific data.
            See GlobalPlatform CardSpecification v2.3Section 11.11 for details."""
            response_permitted = opts.response == 'may_be_returned'
            self.store_data(h2b(opts.DATA), opts.data_structure, opts.encryption, response_permitted)

        def store_data(self, data: bytes, structure:str = 'none', encryption:str = 'none', response_permitted: bool = False) -> bytes:
            """Perform the GlobalPlatform GET DATA command in order to store some card-specific data.
            See GlobalPlatform CardSpecification v2.3Section 11.11 for details."""
            # Table 11-89 of GP Card Specification v2.3
            remainder = data
            block_nr = 0
            response = ''
            while len(remainder):
                chunk = remainder[:255]
                remainder = remainder[255:]
                p1b = build_construct(ADF_SD.StoreData,
                                      {'last_block': len(remainder) == 0, 'encryption': encryption,
                                       'structure': structure, 'response': response_permitted})
                hdr = "80E2%02x%02x%02x" % (p1b[0], block_nr, len(chunk))
                data, sw = self._cmd.lchan.scc.send_apdu_checksw(hdr + b2h(chunk))
                block_nr += 1
                response += data
            return data

        put_key_parser = argparse.ArgumentParser()
        put_key_parser.add_argument('--old-key-version-nr', type=auto_uint8, default=0, help='Old Key Version Number')
        put_key_parser.add_argument('--key-version-nr', type=auto_uint8, required=True, help='Key Version Number')
        put_key_parser.add_argument('--key-id', type=auto_uint7, required=True, help='Key Identifier (base)')
        put_key_parser.add_argument('--key-type', choices=KeyType.ksymapping.values(), action='append', required=True, help='Key Type')
        put_key_parser.add_argument('--key-data', type=is_hexstr, action='append', required=True, help='Key Data Block')
        put_key_parser.add_argument('--key-check', type=is_hexstr, action='append', help='Key Check Value')

        @cmd2.with_argparser(put_key_parser)
        def do_put_key(self, opts):
            """Perform the GlobalPlatform PUT KEY command in order to store a new key on the card.
            See GlobalPlatform CardSpecification v2.3 Section 11.8 for details.

            Example (SCP80 KIC/KID/KIK):
                put_key --key-version-nr 1 --key-id 0x01    --key-type aes --key-data 000102030405060708090a0b0c0d0e0f
                                                            --key-type aes --key-data 101112131415161718191a1b1c1d1e1f
                                                            --key-type aes --key-data 202122232425262728292a2b2c2d2e2f

            Example (SCP81 TLS-PSK/KEK):
                put_key --key-version-nr 0x40 --key-id 0x01 --key-type tls_psk --key-data 303132333435363738393a3b3c3d3e3f
                                                            --key-type des --key-data 404142434445464748494a4b4c4d4e4f

            """
            if len(opts.key_type) != len(opts.key_data):
                raise ValueError('There must be an equal number of key-type and key-data arguments')
            kdb = []
            for i in range(0, len(opts.key_type)):
                if opts.key_check and len(opts.key_check) > i:
                    kcv = opts.key_check[i]
                else:
                    kcv = ''
                kdb.append({'key_type': opts.key_type[i], 'kcb': opts.key_data[i], 'kcv': kcv})
            p2 = opts.key_id
            if len(opts.key_type) > 1:
                p2 |= 0x80
            self.put_key(opts.old_key_version_nr, opts.key_version_nr, p2, kdb)

        # Table 11-68: Key Data Field - Format 1 (Basic Format)
        KeyDataBasic = GreedyRange(Struct('key_type'/KeyType,
                                          'kcb'/HexAdapter(Prefixed(Int8ub, GreedyBytes)),
                                          'kcv'/HexAdapter(Prefixed(Int8ub, GreedyBytes))))

        def put_key(self, old_kvn:int, kvn: int, kid: int, key_dict: dict) -> bytes:
            """Perform the GlobalPlatform PUT KEY command in order to store a new key on the card.
            See GlobalPlatform CardSpecification v2.3 Section 11.8 for details."""
            key_data = kvn.to_bytes(1, 'big') + build_construct(ADF_SD.AddlShellCommands.KeyDataBasic, key_dict)
            hdr = "80D8%02x%02x%02x" % (old_kvn, kid, len(key_data))
            data, sw = self._cmd.lchan.scc.send_apdu_checksw(hdr + b2h(key_data))
            return data

        get_status_parser = argparse.ArgumentParser()
        get_status_parser.add_argument('subset', choices=StatusSubset.ksymapping.values(),
                                       help='Subset of statuses to be included in the response')
        get_status_parser.add_argument('--aid', type=is_hexstr, default='',
                                       help='AID Search Qualifier (search only for given AID)')

        @cmd2.with_argparser(get_status_parser)
        def do_get_status(self, opts):
            """Perform GlobalPlatform GET STATUS command in order to retrieve status information
            on Issuer Security Domain, Executable Load File, Executable Module or Applications."""
            grd_list = self.get_status(opts.subset, opts.aid)
            for grd in grd_list:
                self._cmd.poutput_json(grd.to_dict())

        def get_status(self, subset:str, aid_search_qualifier:Hexstr = '') -> List[GpRegistryRelatedData]:
            subset_hex = b2h(build_construct(StatusSubset, subset))
            aid = ApplicationAID(decoded=aid_search_qualifier)
            cmd_data = aid.to_tlv() + h2b('5c054f9f70c5cc')
            p2 = 0x02 # TLV format according to Table 11-36
            grd_list = []
            while True:
                hdr = "80F2%s%02x%02x" % (subset_hex, p2, len(cmd_data))
                data, sw = self._cmd.lchan.scc.send_apdu(hdr + b2h(cmd_data))
                remainder = h2b(data)
                while len(remainder):
                    # tlv sequence, each element is one GpRegistryRelatedData()
                    grd = GpRegistryRelatedData()
                    dec, remainder = grd.from_tlv(remainder)
                    grd_list.append(grd)
                if sw != '6310':
                    return grd_list
                else:
                    p2 |= 0x01
            return grd_list

        set_status_parser = argparse.ArgumentParser()
        set_status_parser.add_argument('scope', choices=SetStatusScope.ksymapping.values(),
                                       help='Defines the scope of the requested status change')
        set_status_parser.add_argument('status', choices=CLifeCycleState.ksymapping.values(),
                                       help='Specify the new intended status')
        set_status_parser.add_argument('--aid', type=is_hexstr,
                                       help='AID of the target Application or Security Domain')

        @cmd2.with_argparser(set_status_parser)
        def do_set_status(self, opts):
            """Perform GlobalPlatform SET STATUS command in order to change the life cycle state of the
            Issuer Security Domain, Supplementary Security Domain or Application.  This normally requires
            prior authentication with a Secure Channel Protocol."""
            self.set_status(opts.scope, opts.status, opts.aid)

        def set_status(self, scope:str, status:str, aid:Hexstr = ''):
            SetStatus = Struct(Const(0x80, Byte), Const(0xF0, Byte),
                               'scope'/SetStatusScope, 'status'/CLifeCycleState,
                               'aid'/HexAdapter(Prefixed(Int8ub, COptional(GreedyBytes))))
            apdu = build_construct(SetStatus, {'scope':scope, 'status':status, 'aid':aid})
            data, sw = self._cmd.lchan.scc.send_apdu_checksw(b2h(apdu))

        inst_perso_parser = argparse.ArgumentParser()
        inst_perso_parser.add_argument('application-aid', type=is_hexstr, help='Application AID')

        @cmd2.with_argparser(inst_perso_parser)
        def do_install_for_personalization(self, opts):
            """Perform GlobalPlatform INSTALL [for personalization] command in order toinform a Security
            Domain that the following STORE DATA commands are meant for a specific AID (specified here)."""
            # Section 11.5.2.3.6 / Table 11-47
            self.install(0x20, 0x00, "0000%02u%s000000" % (len(opts.application_aid)//2, opts.application_aid))

        def install(self, p1:int, p2:int, data:Hexstr) -> ResTuple:
            cmd_hex = "80E6%02x%02x%02x%s" % (p1, p2, len(data)//2, data)
            return self._cmd.lchan.scc.send_apdu_checksw(cmd_hex)

        del_cc_parser = argparse.ArgumentParser()
        del_cc_parser.add_argument('aid', type=is_hexstr,
                                   help='Executable Load File or Application AID')
        del_cc_parser.add_argument('--delete-related-objects', action='store_true',
                                   help='Delete not only the object but also its related objects')

        @cmd2.with_argparser(del_cc_parser)
        def do_delete_card_content(self, opts):
            """Perform a GlobalPlatform DELETE [card content] command in order to delete an Executable Load
            File, an Application or an Executable Load File and its related Applications."""
            p2 = 0x80 if opts.delete_related_objects else 0x00
            aid = ApplicationAID(decoded=opts.aid)
            self.delete(0x00, p2, b2h(aid.to_tlv()))

        del_key_parser = argparse.ArgumentParser()
        del_key_parser.add_argument('--key-id', type=auto_uint7, help='Key Identifier (KID)')
        del_key_parser.add_argument('--key-ver', type=auto_uint8, help='Key Version Number (KVN)')
        del_key_parser.add_argument('--delete-related-objects', action='store_true',
                                   help='Delete not only the object but also its related objects')

        @cmd2.with_argparser(del_key_parser)
        def do_delete_key(self, opts):
            """Perform GlobalPlaform DELETE (Key) command.
            If both KID and KVN are specified, exactly one key is deleted. If only either of the two is
            specified, multiple matching keys may be deleted."""
            if opts.key_id == None and opts.key_ver == None:
                raise ValueError('At least one of KID or KVN must be specified')
            p2 = 0x80 if opts.delete_related_objects else 0x00
            cmd = ""
            if opts.key_id != None:
                cmd += "d001%02x" % opts.key_id
            if opts.key_ver != None:
                cmd += "d201%02x" % opts.key_ver
            self.delete(0x00, p2, cmd)

        def delete(self, p1:int, p2:int, data:Hexstr) -> ResTuple:
            cmd_hex = "80E4%02x%02x%02x%s" % (p1, p2, len(data)//2, data)
            return self._cmd.lchan.scc.send_apdu_checksw(cmd_hex)

        est_scp02_parser = argparse.ArgumentParser()
        est_scp02_parser.add_argument('--key-ver', type=auto_uint8, required=True,
                                      help='Key Version Number (KVN)')
        est_scp02_parser.add_argument('--key-enc', type=is_hexstr, required=True,
                                      help='Secure Channel Encryption Key')
        est_scp02_parser.add_argument('--key-mac', type=is_hexstr, required=True,
                                      help='Secure Channel MAC Key')
        est_scp02_parser.add_argument('--key-dek', type=is_hexstr, required=True,
                                      help='Data Encryption Key')
        est_scp02_parser.add_argument('--host-challenge', type=is_hexstr,
                                      help='Hard-code the host challenge; default: random')
        est_scp02_parser.add_argument('--security-level', type=auto_uint8, default=0x01,
                                      help='Security Level. Default: 0x01 (C-MAC only)')

        @cmd2.with_argparser(est_scp02_parser)
        def do_establish_scp02(self, opts):
            """Establish a secure channel using the GlobalPlatform SCP02 protocol.  It can be released
            again by using `release_scp`."""
            if self._cmd.lchan.scc.scp:
                self._cmd.poutput("Cannot establish SCP02 as this lchan already has a SCP instance!")
                return
            host_challenge = h2b(opts.host_challenge) if opts.host_challenge else get_random_bytes(8)
            kset = GpCardKeyset(opts.key_ver, h2b(opts.key_enc), h2b(opts.key_mac), h2b(opts.key_dek))
            scp02 = SCP02(card_keys=kset)
            self._establish_scp(scp02, host_challenge, opts.security_level)

        est_scp03_parser = deepcopy(est_scp02_parser)
        est_scp03_parser.add_argument('--s16-mode', action='store_true', help='S16 mode (S8 is default)')

        @cmd2.with_argparser(est_scp03_parser)
        def do_establish_scp03(self, opts):
            """Establish a secure channel using the GlobalPlatform SCP03 protocol.  It can be released
            again by using `release_scp`."""
            if self._cmd.lchan.scc.scp:
                self._cmd.poutput("Cannot establish SCP03 as this lchan already has a SCP instance!")
                return
            s_mode = 16 if opts.s16_mode else 8
            host_challenge = h2b(opts.host_challenge) if opts.host_challenge else get_random_bytes(s_mode)
            kset = GpCardKeyset(opts.key_ver, h2b(opts.key_enc), h2b(opts.key_mac), h2b(opts.key_dek))
            scp03 = SCP03(card_keys=kset, s_mode = s_mode)
            self._establish_scp(scp03, host_challenge, opts.security_level)

        def _establish_scp(self, scp, host_challenge, security_level):
            # perform the common functionality shared by SCP02 and SCP03 establishment
            init_update_apdu = scp.gen_init_update_apdu(host_challenge=host_challenge)
            init_update_resp, sw = self._cmd.lchan.scc.send_apdu_checksw(b2h(init_update_apdu))
            scp.parse_init_update_resp(h2b(init_update_resp))
            ext_auth_apdu = scp.gen_ext_auth_apdu(security_level)
            ext_auth_resp, sw = self._cmd.lchan.scc.send_apdu_checksw(b2h(ext_auth_apdu))
            self._cmd.poutput("Successfully established a %s secure channel" % str(scp))
            # store a reference to the SCP instance
            self._cmd.lchan.scc.scp = scp
            self._cmd.update_prompt()


        def do_release_scp(self, opts):
            """Release a previously establiehed secure channel."""
            if not self._cmd.lchan.scc.scp:
                self._cmd.poutput("Cannot release SCP as none is established")
                return
            self._cmd.lchan.scc.scp = None
            self._cmd.update_prompt()


# Card Application of a Security Domain
class CardApplicationSD(CardApplication):
    __intermediate = True
    def __init__(self, aid: str, name: str, desc: str):
        super().__init__(name, adf=ADF_SD(aid, name, desc), sw=sw_table)

# Card Application of Issuer Security Domain
class CardApplicationISD(CardApplicationSD):
    # FIXME: ISD AID is not static, but could be different. One can select the empty
    # application using '00a4040000' and then parse the response FCI to get the ISD AID
    def __init__(self, aid='a000000003000000'):
        super().__init__(aid=aid, name='ADF.ISD', desc='Issuer Security Domain')

#class CardProfileGlobalPlatform(CardProfile):
#    ORDER = 23
#
#    def __init__(self, name='GlobalPlatform'):
#        super().__init__(name, desc='GlobalPlatfomr 2.1.1', cla=['00','80','84'], sw=sw_table)


class GpCardKeyset:
    """A single set of GlobalPlatform card keys and the associated KVN."""
    def __init__(self, kvn: int, enc: bytes, mac: bytes, dek: bytes):
        assert kvn >= 0 and kvn < 256
        assert len(enc) == len(mac) == len(dek)
        self.kvn = kvn
        self.enc = enc
        self.mac = mac
        self.dek = dek

    @classmethod
    def from_single_key(cls, kvn: int, base_key: bytes) -> 'GpCardKeyset':
        return cls(int, base_key, base_key, base_key)

    def __str__(self):
        return "%s(KVN=%u, ENC=%s, MAC=%s, DEK=%s)" % (self.__class__.__name__,
                self.kvn, b2h(self.enc), b2h(self.mac), b2h(self.dek))

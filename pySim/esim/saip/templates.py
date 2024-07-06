# Implementation of SimAlliance/TCA Interoperable Profile Template handling
#
# (C) 2024 by Harald Welte <laforge@osmocom.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from typing import *
from copy import deepcopy
import pySim.esim.saip.oid as OID

class FileTemplate:
    """Representation of a single file in a SimAlliance/TCA Profile Template."""
    def __init__(self, fid:int, name:str, ftype, nb_rec: Optional[int], size:Optional[int], arr:int,
                 sfi:Optional[int] = None, default_val:Optional[str] = None, content_rqd:bool = True,
                 params:Optional[List] = None, ass_serv:Optional[List[int]]=None, high_update:bool = False,
                 pe_name:Optional[str] = None):
        # initialize from arguments
        self.fid = fid
        self.name = name
        if pe_name:
            self.pe_name = pe_name
        else:
            self.pe_name = self.name.replace('.','-').replace('_','-').lower()
        self.file_type = ftype
        if ftype in ['LF', 'CY']:
            self.nb_rec = nb_rec
            self.rec_len = size
        elif ftype in ['TR']:
            self.file_size = size
        self.arr = arr
        self.sfi = sfi
        self.default_val = default_val
        self.content_rqd = content_rqd
        self.params = params
        self.ass_serv = ass_serv
        self.high_update = high_update
        # initialize empty
        self.parent = None
        self.children = []

    def __str__(self) -> str:
        return "FileTemplate(%s)" % (self.name)

    def __repr__(self) -> str:
        s_fid = "%04x" % self.fid if self.fid is not None else 'None'
        s_arr = self.arr if self.arr is not None else 'None'
        s_sfi = "%02x" % self.sfi if self.sfi is not None else 'None'
        return "FileTemplate(%s/%s, %s, %s, arr=%s, sfi=%s)" % (self.name, self.pe_name, s_fid,
                                                                self.file_type, s_arr, s_sfi)

class ProfileTemplate:
    """Representation of a SimAlliance/TCA Profile Template.  Each Template is identified by its OID and
    consists of a number of file definitions.  We implement each profile template as a class derived from this
    base class.  Each such derived class is a singleton and has no instances."""
    created_by_default: bool = False
    oid: Optional[OID.eOID] = None
    files: List[FileTemplate] = []
    files_by_pename: dict[str,FileTemplate] = {}

    def __init_subclass__(cls, **kwargs):
        """This classmethod is called automatically after executing the subclass body. We use it to
        initialize the cls.files_by_pename from the cls.files"""
        super().__init_subclass__(**kwargs)
        for f in cls.files:
            cls.files_by_pename[f.pe_name] = f
        ProfileTemplateRegistry.add(cls)

class ProfileTemplateRegistry:
    """A registry of profile templates.  Exists as a singleton class with no instances and only
    classmethods."""
    by_oid = {}

    @classmethod
    def add(cls, tpl: ProfileTemplate):
        """Add a ProfileTemplate to the registry.  There can only be one Template per OID."""
        oid_str = str(tpl.oid)
        if oid_str in cls.by_oid:
            raise ValueError("We already have a template for OID %s" % oid_str)
        cls.by_oid[oid_str] = tpl

    @classmethod
    def get_by_oid(cls, oid: Union[List[int], str]) -> Optional[ProfileTemplate]:
        """Look-up the ProfileTemplate based on its OID.  The OID can be given either in dotted-string format,
        or as a list of integers."""
        if not isinstance(oid, str):
            oid = OID.OID.str_from_intlist(oid)
        return cls.by_oid.get(oid, None)

# below are transcribed template definitions from "ANNEX A (Normative): File Structure Templates Definition"
# of "Profile interoperability specification V3.1 Final" (unless other version explicitly specified).

# Section 9.2
class FilesAtMF(ProfileTemplate):
    created_by_default = True
    oid = OID.MF
    files = [
        FileTemplate(0x3f00, 'MF',           'MF', None, None,  14, None, None, None, params=['pinStatusTemplateDO']),
        FileTemplate(0x2f05, 'EF.PL',        'TR', None,    2,   1, 0x05, 'FF...FF', None),
        FileTemplate(0x2f02, 'EF.ICCID',     'TR', None,   10,  11, None, None, True),
        FileTemplate(0x2f00, 'EF.DIR',       'LF', None, None,  10, 0x1e, None, True, params=['nb_rec', 'size']),
        FileTemplate(0x2f06, 'EF.ARR',       'LF', None, None,  10, None, None, True, params=['nb_rec', 'size']),
        FileTemplate(0x2f08, 'EF.UMPC',      'TR', None,    5,  10, 0x08, None, False),
    ]


# Section 9.3
class FilesCD(ProfileTemplate):
    created_by_default = False
    oid = OID.DF_CD
    files = [
        FileTemplate(0x7f11, 'DF.CD',        'DF', None, None,  14, None, None, False, params=['pinStatusTemplateDO']),
        FileTemplate(0x6f01, 'EF.LAUNCHPAD', 'TR', None, None,   2, None, None, True, params=['size']),
    ]
    for i in range(0x40, 0x7f):
        files.append(FileTemplate(0x6f00+i, 'EF.ICON',      'TR', None, None,   2, None, None, True, params=['size']))


# Section 9.4: Do this separately, so we can use them also from 9.5.3
df_pb_files = [
    FileTemplate(0x5f3a, 'DF.PHONEBOOK', 'DF', None, None,  14, None, None, True, ['pinStatusTemplateDO']),
    FileTemplate(0x4f30, 'EF.PBR',       'LF', None, None,   2, None, None, True, ['nb_rec', 'size']),
]
for i in range(0x38, 0x40):
    df_pb_files.append(FileTemplate(0x4f00+i, 'EF.EXT1', 'LF', None,   13,  5, None, '00FF...FF', False, ['size','sfi']))
for i in range(0x40, 0x48):
    df_pb_files.append(FileTemplate(0x4f00+i, 'EF.AAS', 'LF', None, None,  5, None, 'FF...FF', False, ['nb_rec','size']))
for i in range(0x48, 0x50):
    df_pb_files.append(FileTemplate(0x4f00+i, 'EF.GAS', 'LF', None, None,  5, None, 'FF...FF', False, ['nb_rec','size']))
df_pb_files += [
    FileTemplate(0x4f22, 'EF.PSC',       'TR', None,    4,   5, None, '00000000', False, ['sfi']),
    FileTemplate(0x4f23, 'EF.CC',        'TR', None,    2,   5, None, '0000', False, ['sfi'], high_update=True),
    FileTemplate(0x4f24, 'EF.PUID',      'TR', None,    2,   5, None, '0000', False, ['sfi'], high_update=True),
]
for i in range(0x50, 0x58):
    df_pb_files.append(FileTemplate(0x4f00+i, 'EF.IAP', 'LF', None, None,  5, None, 'FF...FF', False, ['nb_rec','size','sfi']))
for i in range(0x58, 0x60):
    df_pb_files.append(FileTemplate(0x4f00+i, 'EF.ADN', 'LF', None, None,  5, None, 'FF...FF', False, ['nb_rec','size','sfi']))
for i in range(0x60, 0x68):
    df_pb_files.append(FileTemplate(0x4f00+i, 'EF.ADN', 'LF', None,    2,  5, None, '00...00', False, ['nb_rec','sfi']))
for i in range(0x68, 0x70):
    df_pb_files.append(FileTemplate(0x4f00+i, 'EF.ANR', 'LF', None, None,  5, None, 'FF...FF', False, ['nb_rec','size','sfi']))
for i in range(0x70, 0x78):
    df_pb_files.append(FileTemplate(0x4f00+i, 'EF.PURI', 'LF', None, None,  5, None, None, True, ['nb_rec','size','sfi']))
for i in range(0x78, 0x80):
    df_pb_files.append(FileTemplate(0x4f00+i, 'EF.EMAIL', 'LF', None, None,  5, None, 'FF...FF', False, ['nb_rec','size','sfi']))
for i in range(0x80, 0x88):
    df_pb_files.append(FileTemplate(0x4f00+i, 'EF.SNE', 'LF', None, None,  5, None, 'FF...FF', False, ['nb_rec','size','sfi']))
for i in range(0x88, 0x90):
    df_pb_files.append(FileTemplate(0x4f00+i, 'EF.UID', 'LF', None,    2,  5, None, '0000', False, ['nb_rec','sfi']))
for i in range(0x90, 0x98):
    df_pb_files.append(FileTemplate(0x4f00+i, 'EF.GRP', 'LF', None, None,  5, None, '00...00', False, ['nb_rec','size','sfi']))
for i in range(0x98, 0xa0):
    df_pb_files.append(FileTemplate(0x4f00+i, 'EF.CCP1', 'LF', None, None,  5, None, 'FF...FF', False, ['nb_rec','size','sfi']))

# Section 9.4 v2.3.1
class FilesTelecom(ProfileTemplate):
    created_by_default = False
    oid = OID.DF_TELECOM
    files = [
        FileTemplate(0x7f11, 'DF.TELECOM',   'DF', None, None,  14, None, None, False, params=['pinStatusTemplateDO']),
        FileTemplate(0x6f06, 'EF.ARR',       'LF', None, None,  10, None, None, True, ['nb_rec', 'size']),
        FileTemplate(0x6f53, 'EF.RMA',       'LF', None, None,   3, None, None, True, ['nb_rec', 'size']),
        FileTemplate(0x6f54, 'EF.SUME',      'TR', None,   22,   3, None, None, True),
        FileTemplate(0x6fe0, 'EF.ICE_DN',    'LF',   50,   24,   9, None, 'FF...FF', False),
        FileTemplate(0x6fe1, 'EF.ICE_FF',    'LF', None, None,   9, None, 'FF...FF', False, ['nb_rec', 'size']),
        FileTemplate(0x6fe5, 'EF.PSISMSC',   'LF', None, None,   5, None, None, True, ['nb_rec', 'size'], ass_serv=[12,91]),
        FileTemplate(0x5f50, 'DF.GRAPHICS',  'DF', None, None,  14, None, None, False, ['pinStatusTemplateDO']),
        FileTemplate(0x4f20, 'EF.IMG',       'LF', None, None,   2, None, '00FF...FF', False, ['nb_rec', 'size']),
        # EF.IIDF below
        FileTemplate(0x4f21, 'EF.ICE_GRAPHICS','BT',None,None,   9, None, None, False, ['size']),
        FileTemplate(0x4f01, 'EF.LAUNCH_SCWS','TR',None, None,  10, None, None, True, ['size']),
        # EF.ICON below
    ]
    for i in range(0x40, 0x80):
        files.append(FileTemplate(0x4f00+i, 'EF.IIDF', 'TR', None, None, 2, None, 'FF...FF', False, ['size']))
    for i in range(0x80, 0xC0):
        files.append(FileTemplate(0x4f00+i, 'EF.ICON', 'TR', None, None, 10, None, None, True, ['size']))

    # we copy the objects (instances) here as we also use them below from FilesUsimDfPhonebook
    files += [deepcopy(x) for x in df_pb_files]

    files += [
        FileTemplate(0x5f3b, 'DF.MULTIMEDIA','DF', None, None,  14, None, None, False, ['pinStatusTemplateDO'], ass_serv=[67]),
        FileTemplate(0x4f47, 'EF.MML',       'BT', None, None,   5, None, None, False, ['size'], ass_serv=[67]),
        FileTemplate(0x4f48, 'EF.MMDF',      'BT', None, None,   5, None, None, False, ['size'], ass_serv=[67]),

        FileTemplate(0x5f3c, 'DF.MMSS',      'DF', None, None,  14, None, None, False, ['pinStatusTemplateDO']),
        FileTemplate(0x4f20, 'EF.MLPL',      'TR', None, None,   2, 0x01, None, True, ['size']),
        FileTemplate(0x4f21, 'EF.MSPL',      'TR', None, None,   2, 0x02, None, True, ['size']),
        FileTemplate(0x4f21, 'EF.MMSSMODE',  'TR', None,    1,   2, 0x03, None, True),
    ]


# Section 9.4
class FilesTelecomV2(ProfileTemplate):
    created_by_default = False
    oid = OID.DF_TELECOM_v2
    files = [
        FileTemplate(0x7f11, 'DF.TELECOM',   'DF', None, None,  14, None, None, False, params=['pinStatusTemplateDO']),
        FileTemplate(0x6f06, 'EF.ARR',       'LF', None, None,  10, None, None, True, ['nb_rec', 'size']),
        FileTemplate(0x6f53, 'EF.RMA',       'LF', None, None,   3, None, None, True, ['nb_rec', 'size']),
        FileTemplate(0x6f54, 'EF.SUME',      'TR', None,   22,   3, None, None, True),
        FileTemplate(0x6fe0, 'EF.ICE_DN',    'LF',   50,   24,   9, None, 'FF...FF', False),
        FileTemplate(0x6fe1, 'EF.ICE_FF',    'LF', None, None,   9, None, 'FF...FF', False, ['nb_rec', 'size']),
        FileTemplate(0x6fe5, 'EF.PSISMSC',   'LF', None, None,   5, None, None, True, ['nb_rec', 'size'], ass_serv=[12,91]),
        FileTemplate(0x5f50, 'DF.GRAPHICS',  'DF', None, None,  14, None, None, False, ['pinStatusTemplateDO']),
        FileTemplate(0x4f20, 'EF.IMG',       'LF', None, None,   2, None, '00FF...FF', False, ['nb_rec', 'size']),
        # EF.IIDF below
        FileTemplate(0x4f21, 'EF.ICE_GRRAPHICS','BT',None,None,   9, None, None, False, ['size']),
        FileTemplate(0x4f01, 'EF.LAUNCH_SCWS','TR',None, None,  10, None, None, True, ['size']),
        # EF.ICON below
    ]
    for i in range(0x40, 0x80):
        files.append(FileTemplate(0x4f00+i, 'EF.IIDF', 'TR', None, None, 2, None, 'FF...FF', False, ['size']))
    for i in range(0x80, 0xC0):
        files.append(FileTemplate(0x4f00+i, 'EF.ICON', 'TR', None, None, 10, None, None, True, ['size']))

    # we copy the objects (instances) here as we also use them below from FilesUsimDfPhonebook
    files += [deepcopy(x) for x in df_pb_files]

    files += [
        FileTemplate(0x5f3b, 'DF.MULTIMEDIA','DF', None, None,  14, None, None, False, ['pinStatusTemplateDO'], ass_serv=[67]),
        FileTemplate(0x4f47, 'EF.MML',       'BT', None, None,   5, None, None, False, ['size'], ass_serv=[67]),
        FileTemplate(0x4f48, 'EF.MMDF',      'BT', None, None,   5, None, None, False, ['size'], ass_serv=[67]),

        FileTemplate(0x5f3c, 'DF.MMSS',      'DF', None, None,  14, None, None, False, ['pinStatusTemplateDO']),
        FileTemplate(0x4f20, 'EF.MLPL',      'TR', None, None,   2, 0x01, None, True, ['size']),
        FileTemplate(0x4f21, 'EF.MSPL',      'TR', None, None,   2, 0x02, None, True, ['size']),
        FileTemplate(0x4f21, 'EF.MMSSMODE',  'TR', None,    1,   2, 0x03, None, True),


        FileTemplate(0x5f3d, 'DF.MCS',       'DF', None, None,  14, None, None, False, ['pinStatusTemplateDO'], ass_serv={'usim':109, 'isim': 15}),
        FileTemplate(0x4f01, 'EF.MST',       'TR', None, None,   2, 0x01, None, True, ['size'], ass_serv={'usim':109, 'isim': 15}),
        FileTemplate(0x4f02, 'EF.MCSCONFIG', 'BT', None, None,   2, 0x02, None, True, ['size'], ass_serv={'usim':109, 'isim': 15}),

        FileTemplate(0x5f3e, 'DF.V2X',       'DF', None, None,  14, None, None, False, ['pinStatusTemplateDO'], ass_serv=[119]),
        FileTemplate(0x4f01, 'EF.VST',       'TR', None, None,   2, 0x01, None, True, ['size'], ass_serv=[119]),
        FileTemplate(0x4f02, 'EF.V2X_CONFIG','BT', None, None,   2, 0x02, None, True, ['size'], ass_serv=[119]),
        FileTemplate(0x4f03, 'EF.V2XP_PC5',  'TR', None, None,   2, None, None, True, ['size'], ass_serv=[119]), # VST: 2
        FileTemplate(0x4f04, 'EF.V2XP_Uu',   'TR', None, None,   2, None, None, True, ['size'], ass_serv=[119]), # VST: 3
    ]


# Section 9.5.1 v2.3.1
class FilesUsimMandatory(ProfileTemplate):
    created_by_default = True
    oid = OID.ADF_USIM_by_default
    files = [
        FileTemplate(  None, 'ADF.USIM',    'ADF', None, None,  14, None, None, False, ['aid', 'temp_fid', 'pinStatusTemplateDO']),
        FileTemplate(0x6f07, 'EF.IMSI',      'TR', None,    9,   2, 0x07, None, True, ['size']),
        FileTemplate(0x6f06, 'EF.ARR',       'LF', None, None,  10, 0x17, None, True, ['nb_rec','size']),
        FileTemplate(0x6f08, 'EF.Keys',      'TR', None,   33,   5, 0x08, '07FF...FF', False, high_update=True),
        FileTemplate(0x6f09, 'EF.KeysPS',    'TR', None,   33,   5, 0x09, '07FF...FF', False, high_update=True, pe_name = 'ef-keysPS'),
        FileTemplate(0x6f31, 'EF.HPPLMN',    'TR', None,    1,   2, 0x12, '0A', False),
        FileTemplate(0x6f38, 'EF.UST',       'TR', None,   14,   2, 0x04, None, True),
        FileTemplate(0x6f3b, 'EF.FDN',       'LF',   20,   26,   8, None, 'FF...FF', False, ass_serv=[2, 89]),
        FileTemplate(0x6f3c, 'EF.SMS',       'LF',   10,  176,   5, None, '00FF...FF', False, ass_serv=[10]),
        FileTemplate(0x6f42, 'EF.SMSP',      'LF',    1,   38,   5, None, 'FF...FF', False, ass_serv=[12]),
        FileTemplate(0x6f43, 'EF.SMSS',      'TR', None,    2,   5, None, 'FFFF', False, ass_serv=[10]),
        FileTemplate(0x6f46, 'EF.SPN',       'TR', None,   17,  10, None, None, True, ass_serv=[19]),
        FileTemplate(0x6f56, 'EF.EST',       'TR', None,    1,   8, 0x05, None, True, ass_serv=[2,6,34,35]),
        FileTemplate(0x6f5b, 'EF.START-HFN', 'TR', None,    6,   5, 0x0f, 'F00000F00000', False, high_update=True),
        FileTemplate(0x6f5c, 'EF.THRESHOLD', 'TR', None,    3,   2, 0x10, 'FFFFFF', False),
        FileTemplate(0x6f73, 'EF.PSLOCI',    'TR', None,   14,   5, 0x0c, 'FFFFFFFFFFFFFFFFFFFF0000FF01', False, high_update=True),
        FileTemplate(0x6f78, 'EF.ACC',       'TR', None,    2,   2, 0x06, None, True),
        FileTemplate(0x6f7b, 'EF.FPLMN',     'TR', None,   12,   5, 0x0d, 'FF...FF', False),
        FileTemplate(0x6f7e, 'EF.LOCI',      'TR', None,   11,   5, 0x0b, 'FFFFFFFFFFFFFF0000FF01', False, high_update=True),
        FileTemplate(0x6fad, 'EF.AD',        'TR', None,    4,  10, 0x03, '00000002', False),
        FileTemplate(0x6fb7, 'EF.ECC',       'LF',    1,    4,  10, 0x01, None, True),
        FileTemplate(0x6fc4, 'EF.NETPAR',    'TR', None,  128,   5, None, 'FF...FF', False, high_update=True),
        FileTemplate(0x6fe3, 'EF.EPSLOCI',   'TR', None,   18,   5, 0x1e, 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFF000001', False, ass_serv=[85], high_update=True),
        FileTemplate(0x6fe4, 'EF.EPSNSC',    'LF',    1,   80,   5, 0x18, 'FF...FF', False, ass_serv=[85], high_update=True),
    ]

# Section 9.5.1
class FilesUsimMandatoryV2(ProfileTemplate):
    created_by_default = True
    oid = OID.ADF_USIM_by_default_v2
    files = [
        FileTemplate(  None, 'ADF.USIM',    'ADF', None, None,  14, None, None, False, ['aid', 'temp_fid', 'pinStatusTemplateDO']),
        FileTemplate(0x6f07, 'EF.IMSI',      'TR', None,    9,   2, 0x07, None, True, ['size']),
        FileTemplate(0x6f06, 'EF.ARR',       'LF', None, None,  10, 0x17, None, True, ['nb_rec','size']),
        FileTemplate(0x6f08, 'EF.Keys',      'TR', None,   33,   5, 0x08, '07FF...FF', False, high_update=True),
        FileTemplate(0x6f09, 'EF.KeysPS',    'TR', None,   33,   5, 0x09, '07FF...FF', False, high_update=True, pe_name='ef-keysPS'),
        FileTemplate(0x6f31, 'EF.HPPLMN',    'TR', None,    1,   2, 0x12, '0A', False),
        FileTemplate(0x6f38, 'EF.UST',       'TR', None,   17,   2, 0x04, None, True),
        FileTemplate(0x6f3b, 'EF.FDN',       'LF',   20,   26,   8, None, 'FF...FF', False, ass_serv=[2, 89]),
        FileTemplate(0x6f3c, 'EF.SMS',       'LF',   10,  176,   5, None, '00FF...FF', False, ass_serv=[10]),
        FileTemplate(0x6f42, 'EF.SMSP',      'LF',    1,   38,   5, None, 'FF...FF', False, ass_serv=[12]),
        FileTemplate(0x6f43, 'EF.SMSS',      'TR', None,    2,   5, None, 'FFFF', False, ass_serv=[10]),
        FileTemplate(0x6f46, 'EF.SPN',       'TR', None,   17,  10, None, None, True, ass_serv=[19]),
        FileTemplate(0x6f56, 'EF.EST',       'TR', None,    1,   8, 0x05, None, True, ass_serv=[2,6,34,35]),
        FileTemplate(0x6f5b, 'EF.START-HFN', 'TR', None,    6,   5, 0x0f, 'F00000F00000', False, high_update=True),
        FileTemplate(0x6f5c, 'EF.THRESHOLD', 'TR', None,    3,   2, 0x10, 'FFFFFF', False),
        FileTemplate(0x6f73, 'EF.PSLOCI',    'TR', None,   14,   5, 0x0c, 'FFFFFFFFFFFFFFFFFFFF0000FF01', False, high_update=True),
        FileTemplate(0x6f78, 'EF.ACC',       'TR', None,    2,   2, 0x06, None, True),
        FileTemplate(0x6f7b, 'EF.FPLMN',     'TR', None,   12,   5, 0x0d, 'FF...FF', False),
        FileTemplate(0x6f7e, 'EF.LOCI',      'TR', None,   11,   5, 0x0b, 'FFFFFFFFFFFFFF0000FF01', False, high_update=True),
        FileTemplate(0x6fad, 'EF.AD',        'TR', None,    4,  10, 0x03, '00000002', False),
        FileTemplate(0x6fb7, 'EF.ECC',       'LF',    1,    4,  10, 0x01, None, True),
        FileTemplate(0x6fc4, 'EF.NETPAR',    'TR', None,  128,   5, None, 'FF...FF', False, high_update=True),
        FileTemplate(0x6fe3, 'EF.EPSLOCI',   'TR', None,   18,   5, 0x1e, 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFF000001', False, ass_serv=[85], high_update=True),
        FileTemplate(0x6fe4, 'EF.EPSNSC',    'LF',    1,   80,   5, 0x18, 'FF...FF', False, ass_serv=[85], high_update=True),
    ]


# Section 9.5.2 v2.3.1
class FilesUsimOptional(ProfileTemplate):
    created_by_default = False
    oid = OID.ADF_USIMopt_not_by_default
    files = [
        FileTemplate(0x6f05, 'EF.LI',        'TR', None,    6,   1, 0x02, 'FF...FF', False),
        FileTemplate(0x6f37, 'EF.ACMmax',    'TR', None,    3,   5, None, '000000', False, ass_serv=[13], pe_name='ef-acmax'),
        FileTemplate(0x6f39, 'EF.ACM',       'CY',    1,    3,   7, None, '000000', False, ass_serv=[13], high_update=True),
        FileTemplate(0x6f3e, 'EF.GID1',      'TR', None,    8,   2, None, None, True, ass_serv=[17]),
        FileTemplate(0x6f3f, 'EF.GID2',      'TR', None,    8,   2, None, None, True, ass_serv=[18]),
        FileTemplate(0x6f40, 'EF.MSISDN',    'LF',    1,   24,   2, None, 'FF...FF', False, ass_serv=[21]),
        FileTemplate(0x6f41, 'EF.PUCT',      'TR', None,    5,   5, None, 'FFFFFF0000', False, ass_serv=[13]),
        FileTemplate(0x6f45, 'EF.CBMI',      'TR', None,   10,   5, None, 'FF...FF', False, ass_serv=[15]),
        FileTemplate(0x6f48, 'EF.CBMID',     'TR', None,   10,   2, 0x0e, 'FF...FF', False, ass_serv=[19]),
        FileTemplate(0x6f49, 'EF.SDN',       'LF',   10,   24,   2, None, 'FF...FF', False, ass_serv=[4,89]),
        FileTemplate(0x6f4b, 'EF.EXT2',      'LF',   10,   13,   8, None, '00FF...FF', False, ass_serv=[3]),
        FileTemplate(0x6f4c, 'EF.EXT3',      'LF',   10,   13,   2, None, '00FF...FF', False, ass_serv=[5]),
        FileTemplate(0x6f50, 'EF.CBMIR',     'TR', None,   20,   5, None, 'FF...FF', False, ass_serv=[16]),
        FileTemplate(0x6f60, 'EF.PLMNwAcT',  'TR', None,   40,   5, 0x0a, 'FFFFFF0000'*8, False, ass_serv=[20]),
        FileTemplate(0x6f61, 'EF.OPLMNwAcT', 'TR', None,   40,   2, 0x11, 'FFFFFF0000'*8, False, ass_serv=[42]),
        FileTemplate(0x6f62, 'EF.HPLMNwAcT', 'TR', None,    5,   2, 0x13, 'FFFFFF0000', False, ass_serv=[43]),
        FileTemplate(0x6f2c, 'EF.DCK',       'TR', None,   16,   5, None, 'FF...FF', False, ass_serv=[36]),
        FileTemplate(0x6f32, 'EF.CNL',       'TR', None,   30,   2, None, 'FF...FF', False, ass_serv=[37]),
        FileTemplate(0x6f47, 'EF.SMSR',      'LF',   10,   30,   5, None, '00FF...FF', False, ass_serv=[11]),
        FileTemplate(0x6f4d, 'EF.BDN',       'LF',   10,   25,   8, None, 'FF...FF', False, ass_serv=[6]),
        FileTemplate(0x6f4e, 'EF.EXT5',      'LF',   10,   13,   5, None, '00FF...FF', False, ass_serv=[44]),
        FileTemplate(0x6f4f, 'EF.CCP2',      'LF',    5,   15,   5, 0x16, 'FF...FF', False, ass_serv=[14]),
        FileTemplate(0x6f55, 'EF.EXT4',      'LF',   10,   13,   8, None, '00FF...FF', False, ass_serv=[7]),
        FileTemplate(0x6f57, 'EF.ACL',       'TR', None,  101,   8, None, '00FF...FF', False, ass_serv=[35]),
        FileTemplate(0x6f58, 'EF.CMI',       'LF',   10,   11,   2, None, 'FF...FF', False, ass_serv=[6]),
        FileTemplate(0x6f80, 'EF.ICI',       'CY',   20,   38,   5, 0x14, 'FF...FF0000000001FFFF', False, ass_serv=[9], high_update=True),
        FileTemplate(0x6f81, 'EF.OCI',       'CY',   20,   37,   5, 0x15, 'FF...FF00000001FFFF', False, ass_serv=[8], high_update=True),
        FileTemplate(0x6f82, 'EF.ICT',       'CY',    1,    3,   7, None, '000000', False, ass_serv=[9], high_update=True),
        FileTemplate(0x6f83, 'EF.OCT',       'CY',    1,    3,   7, None, '000000', False, ass_serv=[8], high_update=True),
        FileTemplate(0x6fb1, 'EF.VGCS',      'TR', None,   20,   2, None, None, True, ass_serv=[57]),
        FileTemplate(0x6fb2, 'EF.VGCSS',     'TR', None,    7,   5, None, None, True, ass_serv=[57]),
        FileTemplate(0x6fb3, 'EF.VBS',       'TR', None,   20,   2, None, None, True, ass_serv=[58]),
        FileTemplate(0x6fb4, 'EF.VBSS',      'TR', None,    7,   5, None, None, True, ass_serv=[58]), # ARR 2!??
        FileTemplate(0x6fb5, 'EF.eMLPP',     'TR', None,    2,   2, None, None, True, ass_serv=[24]),
        FileTemplate(0x6fb6, 'EF.AaeM',      'TR', None,    1,   5, None, '00', False, ass_serv=[25]),
        FileTemplate(0x6fc3, 'EF.HiddenKey', 'TR', None,    4,   5, None, 'FF...FF', False),
        FileTemplate(0x6fc5, 'EF.PNN',       'LF',   10,   16,  10, 0x19, None, True, ass_serv=[45]),
        FileTemplate(0x6fc6, 'EF.OPL',       'LF',    5,    8,  10, 0x1a, None, True, ass_serv=[46]),
        FileTemplate(0x6fc7, 'EF.MBDN',      'LF',    3,   24,   5, None, None, True, ass_serv=[47]),
        FileTemplate(0x6fc8, 'EF.EXT6',      'LF',   10,   13,   5, None, '00FF...FF', False, ass_serv=[47]),
        FileTemplate(0x6fc9, 'EF.MBI',       'LF',   10,    5,   5, None, None, True, ass_serv=[47]),
        FileTemplate(0x6fca, 'EF.MWIS',      'LF',   10,    6,   5, None, '00...00', False, ass_serv=[48], high_update=True),
        FileTemplate(0x6fcb, 'EF.CFIS',      'LF',   10,   16,   5, None, '0100FF...FF', False, ass_serv=[49]),
        FileTemplate(0x6fcb, 'EF.EXT7',      'LF',   10,   13,   5, None, '00FF...FF', False, ass_serv=[49]),
        FileTemplate(0x6fcd, 'EF.SPDI',      'TR', None,   17,   2, 0x1b, None, True, ass_serv=[51]),
        FileTemplate(0x6fce, 'EF.MMSN',      'LF',   10,    6,   5, None, '000000FF...FF', False, ass_serv=[52]),
        FileTemplate(0x6fcf, 'EF.EXT8',      'LF',   10,   13,   5, None, '00FF...FF', False, ass_serv=[53]),
        FileTemplate(0x6fd0, 'EF.MMSICP',    'TR', None,  100,   2, None, 'FF...FF', False, ass_serv=[52]),
        FileTemplate(0x6fd1, 'EF.MMSUP',     'LF', None, None,   5, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[52]),
        FileTemplate(0x6fd2, 'EF.MMSUCP',    'TR', None,  100,   5, None, 'FF...FF', False, ass_serv=[52,55]),
        FileTemplate(0x6fd3, 'EF.NIA',       'LF',    5,   11,   2, None, 'FF...FF', False, ass_serv=[56]),
        FileTemplate(0x6fd4, 'EF.VGCSCA',    'TR', None, None,   2, None, '00...00', False, ['size'], ass_serv=[64]),
        FileTemplate(0x6fd5, 'EF.VBSCA',     'TR', None, None,   2, None, '00...00', False, ['size'], ass_serv=[65]),
        FileTemplate(0x6fd6, 'EF.GBABP',     'TR', None, None,   5, None, 'FF...FF', False, ['size'], ass_serv=[68]),
        FileTemplate(0x6fd7, 'EF.MSK',       'LF', None, None,   2, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[69], high_update=True),
        FileTemplate(0x6fd8, 'EF.MUK',       'LF', None, None,   2, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[69]),
        FileTemplate(0x6fd9, 'EF.EHPLMN',    'TR', None,   15,   2, 0x1d, 'FF...FF', False, ass_serv=[71]),
        FileTemplate(0x6fda, 'EF.GBANL',     'LF', None, None,   2, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[68]),
        FileTemplate(0x6fdb, 'EF.EHPLMNPI',  'TR', None,    1,   2, None, '00', False, ass_serv=[71,73]),
        FileTemplate(0x6fdc, 'EF.LRPLMNSI',  'TR', None,    1,   2, None, '00', False, ass_serv=[74]),
        FileTemplate(0x6fdd, 'EF.NAFKCA',    'LF', None, None,   2, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[68,76]),
        FileTemplate(0x6fde, 'EF.SPNI',      'TR', None, None,  10, None, '00FF...FF', False, ['size'], ass_serv=[78]),
        FileTemplate(0x6fdf, 'EF.PNNI',      'LF', None, None,  10, None, '00FF...FF', False, ['nb_rec','size'], ass_serv=[79]),
        FileTemplate(0x6fe2, 'EF.NCP-IP',    'LF', None, None,   2, None, None, True, ['nb_rec','size'], ass_serv=[80]),
        FileTemplate(0x6fe6, 'EF.UFC',       'TR', None,   30,  10, None, '801E60C01E900080040000000000000000F0000000004000000000000080', False),
        FileTemplate(0x6fe8, 'EF.NASCONFIG', 'TR', None,   18,   2, None, None, True, ass_serv=[96]),
        FileTemplate(0x6fe7, 'EF.UICCIARI',  'LF', None, None,   2, None, None, True, ['nb_rec','size'], ass_serv=[95]),
        FileTemplate(0x6fec, 'EF.PWS',       'TR', None, None,  10, None, None, True, ['size'], ass_serv=[97]),
        FileTemplate(0x6fed, 'EF.FDNURI',    'LF', None, None,   8, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[2,99]),
        FileTemplate(0x6fee, 'EF.BDNURI',    'LF', None, None,   8, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[6,99]),
        FileTemplate(0x6fef, 'EF.SDNURI',    'LF', None, None,   2, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[4,99]),
        FileTemplate(0x6ff0, 'EF.IWL',       'LF', None, None,   3, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[102]),
        FileTemplate(0x6ff1, 'EF.IPS',       'CY', None,    4,  10, None, 'FF...FF', False, ['size'], ass_serv=[102], high_update=True),
        FileTemplate(0x6ff2, 'EF.IPD',       'LF', None, None,   3, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[102], high_update=True),
    ]


# Section 9.5.2
class FilesUsimOptionalV2(ProfileTemplate):
    created_by_default = False
    oid = OID.ADF_USIMopt_not_by_default_v2
    files = [
        FileTemplate(0x6f05, 'EF.LI',        'TR', None,    6,   1, 0x02, 'FF...FF', False),
        FileTemplate(0x6f37, 'EF.ACMmax',    'TR', None,    3,   5, None, '000000', False, ass_serv=[13]),
        FileTemplate(0x6f39, 'EF.ACM',       'CY',    1,    3,   7, None, '000000', False, ass_serv=[13], high_update=True),
        FileTemplate(0x6f3e, 'EF.GID1',      'TR', None,    8,   2, None, None, True, ass_serv=[17]),
        FileTemplate(0x6f3f, 'EF.GID2',      'TR', None,    8,   2, None, None, True, ass_serv=[18]),
        FileTemplate(0x6f40, 'EF.MSISDN',    'LF',    1,   24,   2, None, 'FF...FF', False, ass_serv=[21]),
        FileTemplate(0x6f41, 'EF.PUCT',      'TR', None,    5,   5, None, 'FFFFFF0000', False, ass_serv=[13]),
        FileTemplate(0x6f45, 'EF.CBMI',      'TR', None,   10,   5, None, 'FF...FF', False, ass_serv=[15]),
        FileTemplate(0x6f48, 'EF.CBMID',     'TR', None,   10,   2, 0x0e, 'FF...FF', False, ass_serv=[19]),
        FileTemplate(0x6f49, 'EF.SDN',       'LF',   10,   24,   2, None, 'FF...FF', False, ass_serv=[4,89]),
        FileTemplate(0x6f4b, 'EF.EXT2',      'LF',   10,   13,   8, None, '00FF...FF', False, ass_serv=[3]),
        FileTemplate(0x6f4c, 'EF.EXT3',      'LF',   10,   13,   2, None, '00FF...FF', False, ass_serv=[5]),
        FileTemplate(0x6f50, 'EF.CBMIR',     'TR', None,   20,   5, None, 'FF...FF', False, ass_serv=[16]),
        FileTemplate(0x6f60, 'EF.PLMNwAcT',  'TR', None,   40,   5, 0x0a, 'FFFFFF0000'*8, False, ass_serv=[20]),
        FileTemplate(0x6f61, 'EF.OPLMNwAcT', 'TR', None,   40,   2, 0x11, 'FFFFFF0000'*8, False, ass_serv=[42]),
        FileTemplate(0x6f62, 'EF.HPLMNwAcT', 'TR', None,    5,   2, 0x13, 'FFFFFF0000', False, ass_serv=[43]),
        FileTemplate(0x6f2c, 'EF.DCK',       'TR', None,   16,   5, None, 'FF...FF', False, ass_serv=[36]),
        FileTemplate(0x6f32, 'EF.CNL',       'TR', None,   30,   2, None, 'FF...FF', False, ass_serv=[37]),
        FileTemplate(0x6f47, 'EF.SMSR',      'LF',   10,   30,   5, None, '00FF...FF', False, ass_serv=[11]),
        FileTemplate(0x6f4d, 'EF.BDN',       'LF',   10,   25,   8, None, 'FF...FF', False, ass_serv=[6]),
        FileTemplate(0x6f4e, 'EF.EXT5',      'LF',   10,   13,   5, None, '00FF...FF', False, ass_serv=[44]),
        FileTemplate(0x6f4f, 'EF.CCP2',      'LF',    5,   15,   5, 0x16, 'FF...FF', False, ass_serv=[14]),
        FileTemplate(0x6f55, 'EF.EXT4',      'LF',   10,   13,   8, None, '00FF...FF', False, ass_serv=[7]),
        FileTemplate(0x6f57, 'EF.ACL',       'TR', None,  101,   8, None, '00FF...FF', False, ass_serv=[35]),
        FileTemplate(0x6f58, 'EF.CMI',       'LF',   10,   11,   2, None, 'FF...FF', False, ass_serv=[6]),
        FileTemplate(0x6f80, 'EF.ICI',       'CY',   20,   38,   5, 0x14, 'FF...FF0000000001FFFF', False, ass_serv=[9], high_update=True),
        FileTemplate(0x6f81, 'EF.OCI',       'CY',   20,   37,   5, 0x15, 'FF...FF00000001FFFF', False, ass_serv=[8], high_update=True),
        FileTemplate(0x6f82, 'EF.ICT',       'CY',    1,    3,   7, None, '000000', False, ass_serv=[9], high_update=True),
        FileTemplate(0x6f83, 'EF.OCT',       'CY',    1,    3,   7, None, '000000', False, ass_serv=[8], high_update=True),
        FileTemplate(0x6fb1, 'EF.VGCS',      'TR', None,   20,   2, None, None, True, ass_serv=[57]),
        FileTemplate(0x6fb2, 'EF.VGCSS',     'TR', None,    7,   5, None, None, True, ass_serv=[57]),
        FileTemplate(0x6fb3, 'EF.VBS',       'TR', None,   20,   2, None, None, True, ass_serv=[58]),
        FileTemplate(0x6fb4, 'EF.VBSS',      'TR', None,    7,   5, None, None, True, ass_serv=[58]), # ARR 2!??
        FileTemplate(0x6fb5, 'EF.eMLPP',     'TR', None,    2,   2, None, None, True, ass_serv=[24]),
        FileTemplate(0x6fb6, 'EF.AaeM',      'TR', None,    1,   5, None, '00', False, ass_serv=[25]),
        FileTemplate(0x6fc3, 'EF.HiddenKey', 'TR', None,    4,   5, None, 'FF...FF', False),
        FileTemplate(0x6fc5, 'EF.PNN',       'LF',   10,   16,  10, 0x19, None, True, ass_serv=[45]),
        FileTemplate(0x6fc6, 'EF.OPL',       'LF',    5,    8,  10, 0x1a, None, True, ass_serv=[46]),
        FileTemplate(0x6fc7, 'EF.MBDN',      'LF',    3,   24,   5, None, None, True, ass_serv=[47]),
        FileTemplate(0x6fc8, 'EF.EXT6',      'LF',   10,   13,   5, None, '00FF...FF', False, ass_serv=[47]),
        FileTemplate(0x6fc9, 'EF.MBI',       'LF',   10,    5,   5, None, None, True, ass_serv=[47]),
        FileTemplate(0x6fca, 'EF.MWIS',      'LF',   10,    6,   5, None, '00...00', False, ass_serv=[48], high_update=True),
        FileTemplate(0x6fcb, 'EF.CFIS',      'LF',   10,   16,   5, None, '0100FF...FF', False, ass_serv=[49]),
        FileTemplate(0x6fcb, 'EF.EXT7',      'LF',   10,   13,   5, None, '00FF...FF', False, ass_serv=[49]),
        FileTemplate(0x6fcd, 'EF.SPDI',      'TR', None,   17,   2, 0x1b, None, True, ass_serv=[51]),
        FileTemplate(0x6fce, 'EF.MMSN',      'LF',   10,    6,   5, None, '000000FF...FF', False, ass_serv=[52]),
        FileTemplate(0x6fcf, 'EF.EXT8',      'LF',   10,   13,   5, None, '00FF...FF', False, ass_serv=[53]),
        FileTemplate(0x6fd0, 'EF.MMSICP',    'TR', None,  100,   2, None, 'FF...FF', False, ass_serv=[52]),
        FileTemplate(0x6fd1, 'EF.MMSUP',     'LF', None, None,   5, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[52]),
        FileTemplate(0x6fd2, 'EF.MMSUCP',    'TR', None,  100,   5, None, 'FF...FF', False, ass_serv=[52,55]),
        FileTemplate(0x6fd3, 'EF.NIA',       'LF',    5,   11,   2, None, 'FF...FF', False, ass_serv=[56]),
        FileTemplate(0x6fd4, 'EF.VGCSCA',    'TR', None, None,   2, None, '00...00', False, ['size'], ass_serv=[64]),
        FileTemplate(0x6fd5, 'EF.VBSCA',     'TR', None, None,   2, None, '00...00', False, ['size'], ass_serv=[65]),
        FileTemplate(0x6fd6, 'EF.GBABP',     'TR', None, None,   5, None, 'FF...FF', False, ['size'], ass_serv=[68]),
        FileTemplate(0x6fd7, 'EF.MSK',       'LF', None, None,   2, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[69], high_update=True),
        FileTemplate(0x6fd8, 'EF.MUK',       'LF', None, None,   2, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[69]),
        FileTemplate(0x6fd9, 'EF.EHPLMN',    'TR', None,   15,   2, 0x1d, 'FF...FF', False, ass_serv=[71]),
        FileTemplate(0x6fda, 'EF.GBANL',     'LF', None, None,   2, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[68]),
        FileTemplate(0x6fdb, 'EF.EHPLMNPI',  'TR', None,    1,   2, None, '00', False, ass_serv=[71,73]),
        FileTemplate(0x6fdc, 'EF.LRPLMNSI',  'TR', None,    1,   2, None, '00', False, ass_serv=[74]),
        FileTemplate(0x6fdd, 'EF.NAFKCA',    'LF', None, None,   2, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[68,76]),
        FileTemplate(0x6fde, 'EF.SPNI',      'TR', None, None,  10, None, '00FF...FF', False, ['size'], ass_serv=[78]),
        FileTemplate(0x6fdf, 'EF.PNNI',      'LF', None, None,  10, None, '00FF...FF', False, ['nb_rec','size'], ass_serv=[79]),
        FileTemplate(0x6fe2, 'EF.NCP-IP',    'LF', None, None,   2, None, None, True, ['nb_rec','size'], ass_serv=[80]),
        FileTemplate(0x6fe6, 'EF.UFC',       'TR', None,   30,  10, None, '801E60C01E900080040000000000000000F0000000004000000000000080', False),
        FileTemplate(0x6fe8, 'EF.NASCONFIG', 'TR', None,   18,   2, None, None, True, ass_serv=[96]),
        FileTemplate(0x6fe7, 'EF.UICCIARI',  'LF', None, None,   2, None, None, True, ['nb_rec','size'], ass_serv=[95]),
        FileTemplate(0x6fec, 'EF.PWS',       'TR', None, None,  10, None, None, True, ['size'], ass_serv=[97]),
        FileTemplate(0x6fed, 'EF.FDNURI',    'LF', None, None,   8, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[2,99]),
        FileTemplate(0x6fee, 'EF.BDNURI',    'LF', None, None,   8, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[6,99]),
        FileTemplate(0x6fef, 'EF.SDNURI',    'LF', None, None,   2, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[4,99]),
        FileTemplate(0x6ff0, 'EF.IWL',       'LF', None, None,   3, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[102]),
        FileTemplate(0x6ff1, 'EF.IPS',       'CY', None,    4,  10, None, 'FF...FF', False, ['size'], ass_serv=[102], high_update=True),
        FileTemplate(0x6ff2, 'EF.IPD',       'LF', None, None,   3, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[102], high_update=True),
        FileTemplate(0x6ff3, 'EF.EPDGID',    'TR', None, None,   2, None, None, True, ['size'], ass_serv=[(106, 107)]),
        FileTemplate(0x6ff4, 'EF.EPDGSELECTION','TR',None,None,  2, None, None, True, ['size'], ass_serv=[(106, 107)]),
        FileTemplate(0x6ff5, 'EF.EPDGIDEM',  'TR', None, None,   2, None, None, True, ['size'], ass_serv=[(110, 111)]),
        FileTemplate(0x6ff6, 'EF.EPDGIDEMSEL','TR',None, None,   2, None, None, True, ['size'], ass_serv=[(110, 111)]),
        FileTemplate(0x6ff7, 'EF.FromPreferred','TR',None,  1,   2, None, '00', False, ass_serv=[114]),
        FileTemplate(0x6ff8, 'EF.IMSConfigData','BT',None,None,  2, None, None, True, ['size'], ass_serv=[115]),
        FileTemplate(0x6ff9, 'EF.3GPPPSDataOff','TR',None,  4,   2, None, None, True, ass_serv=[117]),
        FileTemplate(0x6ffa, 'EF.3GPPPSDOSLIST','LF',None, None, 2, None, None, True, ['nb_rec','size'], ass_serv=[118]),
        FileTemplate(0x6ffc, 'EF.XCAPConfigData','BT',None,None, 2, None, None, True, ['size'], ass_serv=[120]),
        FileTemplate(0x6ffd, 'EF.EARFCNLIST','TR', None, None,  10, None, None, True, ['size'], ass_serv=[121]),
        FileTemplate(0x6ffd, 'EF.MudMidCfgdata','BT', None, None,2, None, None, True, ['size'], ass_serv=[134]),
    ]


# Section 9.5.3
class FilesUsimDfPhonebook(ProfileTemplate):
    created_by_default = False
    oid = OID.DF_PHONEBOOK_ADF_USIM
    files = df_pb_files


# Section 9.5.4
class FilesUsimDfGsmAccess(ProfileTemplate):
    created_by_default = False
    oid = OID.DF_GSM_ACCESS_ADF_USIM
    files = [
        FileTemplate(0x5f3b, 'DF.GSM-ACCESS','DF', None, None,  14, None, None, False, ['pinStatusTemplateDO'], ass_serv=[27]),
        FileTemplate(0x4f20, 'EF.Kc',        'TR', None,    9,   5, 0x01, 'FF...FF07', False, ass_serv=[27], high_update=True),
        FileTemplate(0x4f52, 'EF.KcGPRS',    'TR', None,    9,   5, 0x02, 'FF...FF07', False, ass_serv=[27], high_update=True),
        FileTemplate(0x4f63, 'EF.CPBCCH',    'TR', None,   10,   5, None, 'FF...FF', False, ass_serv=[39], high_update=True),
        FileTemplate(0x4f64, 'EF.InvScan',   'TR', None,    1,   2, None, '00', False, ass_serv=[40]),
    ]


# Section 9.5.11 v2.3.1
class FilesUsimDf5GS(ProfileTemplate):
    created_by_default = False
    oid = OID.DF_5GS
    files = [
        FileTemplate(0x6fc0, 'DF.5GS',               'DF', None, None,  14, None, None, False, ['pinStatusTemplateDO'], ass_serv=[122,126,127,128,129,130], pe_name='df-df-5gs'),
        FileTemplate(0x4f01, 'EF.5GS3GPPLOCI',       'TR', None,   20,   5, 0x01, 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000001', False, ass_serv=[122], high_update=True),
        FileTemplate(0x4f02, 'EF.5GSN3GPPLOCI',      'TR', None,   20,   5, 0x02, 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000001', False, ass_serv=[122], high_update=True),
        FileTemplate(0x4f03, 'EF.5GS3GPPNSC',        'LF',    1,   57,   5, 0x03, 'FF...FF', False, ass_serv=[122], high_update=True),
        FileTemplate(0x4f04, 'EF.5GSN3GPPNSC',       'LF',    1,   57,   5, 0x04, 'FF...FF', False, ass_serv=[122], high_update=True),
        FileTemplate(0x4f05, 'EF.5GAUTHKEYS',        'TR', None,  110,   5, 0x05, None, True, ass_serv=[123], high_update=True),
        FileTemplate(0x4f06, 'EF.UAC_AIC',           'TR', None,    4,   2, 0x06, None, True, ass_serv=[126]),
        FileTemplate(0x4f07, 'EF.SUCI_Calc_Info',    'TR', None, None,   2, 0x07, 'FF...FF', False, ass_serv=[124]),
        FileTemplate(0x4f08, 'EF.OPL5G',             'LF', None,   10,  10, 0x08, 'FF...FF', False, ['nb_rec'], ass_serv=[129]),
        FileTemplate(0x4f09, 'EF.SUPI_NAI',          'TR', None, None,   2, 0x09, None, True, ['size'], ass_serv=[130]),
        FileTemplate(0x4f0a, 'EF.Routing_Indicator', 'TR', None,    4,   2, 0x0a, 'F0FFFFFF', False, ass_serv=[124]),
    ]


# Section 9.5.11.2
class FilesUsimDf5GSv2(ProfileTemplate):
    created_by_default = False
    oid = OID.DF_5GS_v2
    files = [
        FileTemplate(0x6fc0, 'DF.5GS',               'DF', None, None,  14, None, None, False, ['pinStatusTemplateDO'], ass_serv=[122,126,127,128,129,130], pe_name='df-df-5gs'),
        FileTemplate(0x4f01, 'EF.5GS3GPPLOCI',       'TR', None,   20,   5, 0x01, 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000001', False, ass_serv=[122], high_update=True),
        FileTemplate(0x4f02, 'EF.5GSN3GPPLOCI',      'TR', None,   20,   5, 0x02, 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000001', False, ass_serv=[122], high_update=True),
        FileTemplate(0x4f03, 'EF.5GS3GPPNSC',        'LF',    1,   57,   5, 0x03, 'FF...FF', False, ass_serv=[122], high_update=True),
        FileTemplate(0x4f04, 'EF.5GSN3GPPNSC',       'LF',    1,   57,   5, 0x04, 'FF...FF', False, ass_serv=[122], high_update=True),
        FileTemplate(0x4f05, 'EF.5GAUTHKEYS',        'TR', None,  110,   5, 0x05, None, True, ass_serv=[123], high_update=True),
        FileTemplate(0x4f06, 'EF.UAC_AIC',           'TR', None,    4,   2, 0x06, None, True, ass_serv=[126]),
        FileTemplate(0x4f07, 'EF.SUCI_Calc_Info',    'TR', None, None,   2, 0x07, 'FF...FF', False, ass_serv=[124]),
        FileTemplate(0x4f08, 'EF.OPL5G',             'LF', None,   10,  10, 0x08, 'FF...FF', False, ['nb_rec'], ass_serv=[129]),
        FileTemplate(0x4f09, 'EF.SUPI_NAI',          'TR', None, None,   2, 0x09, None, True, ['size'], ass_serv=[130]),
        FileTemplate(0x4f0a, 'EF.Routing_Indicator', 'TR', None,    4,   2, 0x0a, 'F0FFFFFF', False, ass_serv=[124]),
        FileTemplate(0x4f0b, 'EF.URSP',              'BT', None, None,   2, None, None, False, ass_serv=[132]),
        FileTemplate(0x4f0c, 'EF.TN3GPPSNN',         'TR', None,    1,   2, 0x0c, '00', False, ass_serv=[135]),
    ]


# Section 9.5.11.3
class FilesUsimDf5GSv3(ProfileTemplate):
    created_by_default = False
    oid = OID.DF_5GS_v3
    files = [
        FileTemplate(0x6fc0, 'DF.5GS',               'DF', None, None,  14, None, None, False, ['pinStatusTemplateDO'], ass_serv=[122,126,127,128,129,130], pe_name='df-df-5gs'),
        FileTemplate(0x4f01, 'EF.5GS3GPPLOCI',       'TR', None,   20,   5, 0x01, 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000001', False, ass_serv=[122], high_update=True),
        FileTemplate(0x4f02, 'EF.5GSN3GPPLOCI',      'TR', None,   20,   5, 0x02, 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000001', False, ass_serv=[122], high_update=True),
        FileTemplate(0x4f03, 'EF.5GS3GPPNSC',        'LF',    2,   62,   5, 0x03, 'FF...FF', False, ass_serv=[122,136], high_update=True),
        # ^ If Service n°136 is not "available" in EF UST, the Profile Creator shall ensure that these files shall contain one record; otherwise, they shall contain 2 records.
        FileTemplate(0x4f04, 'EF.5GSN3GPPNSC',       'LF',    2,   62,   5, 0x04, 'FF...FF', False, ass_serv=[122,136], high_update=True),
        # ^ If Service n°136 is not "available" in EF UST, the Profile Creator shall ensure that these files shall contain one record; otherwise, they shall contain 2 records.
        FileTemplate(0x4f05, 'EF.5GAUTHKEYS',        'TR', None,  110,   5, 0x05, None, True, ass_serv=[123], high_update=True),
        FileTemplate(0x4f06, 'EF.UAC_AIC',           'TR', None,    4,   2, 0x06, None, True, ass_serv=[126]),
        FileTemplate(0x4f07, 'EF.SUCI_Calc_Info',    'TR', None, None,   2, 0x07, 'FF...FF', False, ass_serv=[124]),
        FileTemplate(0x4f08, 'EF.OPL5G',             'LF', None,   10,  10, 0x08, 'FF...FF', False, ['nb_rec'], ass_serv=[129]),
        FileTemplate(0x4f09, 'EF.SUPI_NAI',          'TR', None, None,   2, 0x09, None, True, ['size'], ass_serv=[130], pe_name='ef-supinai'),
        FileTemplate(0x4f0a, 'EF.Routing_Indicator', 'TR', None,    4,   2, 0x0a, 'F0FFFFFF', False, ass_serv=[124]),
        FileTemplate(0x4f0b, 'EF.URSP',              'BT', None, None,   2, None, None, False, ass_serv=[132]),
        FileTemplate(0x4f0c, 'EF.TN3GPPSNN',         'TR', None,    1,   2, 0x0c, '00', False, ass_serv=[135]),
    ]


# Section 9.5.12
class FilesUsimDfSaip(ProfileTemplate):
    created_by_default = False
    oid = OID.DF_SAIP
    files = [
        FileTemplate(0x6fd0, 'DF.SAIP',        'DF', None, None,  14, None, None, False, ['pinStatusTemplateDO'], ass_serv=[(124, 125)], pe_name='df-df-saip'),
        FileTemplate(0x4f01, 'EF.SUCICalcInfo','TR', None, None, 3, None, 'FF..FF', False, ['size'], ass_serv=[125], pe_name='ef-suci-calc-info-usim'),
    ]


# Section 9.6.1
class FilesIsimMandatory(ProfileTemplate):
    created_by_default = True
    oid = OID.ADF_ISIM_by_default
    files = [
        FileTemplate(  None, 'ADF.ISIM',      'ADF', None, None,  14, None, None, False, ['aid','temporary_fid','pinStatusTemplateDO']),
        FileTemplate(0x6f02, 'EF.IMPI',        'TR', None, None,   2, 0x02, None, True, ['size']),
        FileTemplate(0x6f04, 'EF.IMPU',        'LF',    1, None,   2, 0x04, None, True, ['size']),
        FileTemplate(0x6f03, 'EF.Domain',      'TR', None, None,   2, 0x05, None, True, ['size']),
        FileTemplate(0x6f07, 'EF.IST',         'TR', None,   14,   2, 0x07, None, True),
        FileTemplate(0x6fad, 'EF.AD',          'TR', None,    3,  10, 0x03, '000000', False),
        FileTemplate(0x6f06, 'EF.ARR',         'LF', None, None,  10, 0x06, None, True, ['nb_rec','size']),
    ]


# Section 9.6.2 v2.3.1
class FilesIsimOptional(ProfileTemplate):
    created_by_default = False
    oid = OID.ADF_ISIMopt_not_by_default
    files = [
        FileTemplate(0x6f09, 'EF.P-CSCF',      'LF',    1, None,   2, None, None, True, ['size'], ass_serv=[1,5]),
        FileTemplate(0x6f3c, 'EF.SMS',         'LF',   10,  176,   5, None, '00FF...FF', False, ass_serv=[6,8]),
        FileTemplate(0x6f42, 'EF.SMSP',        'LF',    1,   38,   5, None, 'FF...FF', False, ass_serv=[8]),
        FileTemplate(0x6f43, 'EF.SMSS',        'TR', None,    2,   5, None, 'FFFF', False, ass_serv=[6,8]),
        FileTemplate(0x6f47, 'EF.SMSR',        'LF',   10,   30,   5, None, '00FF...FF', False, ass_serv=[7,8]),
        FileTemplate(0x6fd5, 'EF.GBABP',       'TR', None, None,   5, None, 'FF...FF', False, ['size'], ass_serv=[2]),
        FileTemplate(0x6fd7, 'EF.GBANL',       'LF', None, None,   2, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[2]),
        FileTemplate(0x6fdd, 'EF.NAFKCA',      'LF', None, None,   2, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[2,4]),
        FileTemplate(0x6fe7, 'EF.UICCIARI',    'LF', None, None,   2, None, None, True, ['nb_rec','size'], ass_serv=[10]),
    ]


# Section 9.6.2
class FilesIsimOptionalv2(ProfileTemplate):
    created_by_default = False
    oid = OID.ADF_ISIMopt_not_by_default_v2
    files = [
        FileTemplate(0x6f09, 'EF.PCSCF',       'LF',    1, None,   2, None, None, True, ['size'], ass_serv=[1,5]),
        FileTemplate(0x6f3c, 'EF.SMS',         'LF',   10,  176,   5, None, '00FF...FF', False, ass_serv=[6,8]),
        FileTemplate(0x6f42, 'EF.SMSP',        'LF',    1,   38,   5, None, 'FF...FF', False, ass_serv=[8]),
        FileTemplate(0x6f43, 'EF.SMSS',        'TR', None,    2,   5, None, 'FFFF', False, ass_serv=[6,8]),
        FileTemplate(0x6f47, 'EF.SMSR',        'LF',   10,   30,   5, None, '00FF...FF', False, ass_serv=[7,8]),
        FileTemplate(0x6fd5, 'EF.GBABP',       'TR', None, None,   5, None, 'FF...FF', False, ['size'], ass_serv=[2]),
        FileTemplate(0x6fd7, 'EF.GBANL',       'LF', None, None,   2, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[2]),
        FileTemplate(0x6fdd, 'EF.NAFKCA',      'LF', None, None,   2, None, 'FF...FF', False, ['nb_rec','size'], ass_serv=[2,4]),
        FileTemplate(0x6fe7, 'EF.UICCIARI',    'LF', None, None,   2, None, None, True, ['nb_rec','size'], ass_serv=[10]),
        FileTemplate(0x6ff7, 'EF.FromPreferred','TR', None,   1,   2, None, '00', False, ass_serv=[17]),
        FileTemplate(0x6ff8, 'EF.ImsConfigData','BT', None,None,   2, None, None, True, ['size'], ass_serv=[18]),
        FileTemplate(0x6ffc, 'EF.XcapconfigData','BT',None,None,   2, None, None, True, ['size'], ass_serv=[19]),
        FileTemplate(0x6ffa, 'EF.WebRTCURI',   'LF', None, None,   2, None, None, True, ['nb_rec', 'size'], ass_serv=[20]),
        FileTemplate(0x6ffa, 'EF.MudMidCfgData','BT',None, None,   2, None, None, True, ['size'], ass_serv=[21]),
    ]


# TODO: CSIM


# Section 9.8
class FilesEap(ProfileTemplate):
    created_by_default = False
    oid = OID.DF_EAP
    files = [
        FileTemplate(  None, 'DF.EAP',         'DF', None, None,  14, None, None, False, ['fid','pinStatusTemplateDO'], ass_serv=[(124, 125)]),
        FileTemplate(0x4f01, 'EF.EAPKEYS',     'TR', None, None,   2, None, None, True, ['size'], high_update=True),
        FileTemplate(0x4f02, 'EF.EAPSTATUS',   'TR', None,    1,   2, None, '00', False, high_update=True),
        FileTemplate(0x4f03, 'EF.PUId',        'TR', None, None,   2, None, None, True, ['size']),
        FileTemplate(0x4f04, 'EF.Ps',          'TR', None, None,   5, None, 'FF..FF', False, ['size'], high_update=True),
        FileTemplate(0x4f20, 'EF.CurID',       'TR', None, None,   5, None, 'FF..FF', False, ['size'], high_update=True),
        FileTemplate(0x4f21, 'EF.RelID',       'TR', None, None,   5, None, None, True, ['size']),
        FileTemplate(0x4f22, 'EF.Realm',       'TR', None, None,   5, None, None, True, ['size']),
    ]


# Section 9.9 Access Rules Definition
ARR_DEFINITION = {
     1: ['8001019000', '800102A406830101950108', '800158A40683010A950108'],
     2: ['800101A406830101950108', '80015AA40683010A950108'],
     3: ['80015BA40683010A950108'],
     4: ['8001019000', '80011A9700', '800140A40683010A950108'],
     5: ['800103A406830101950108', '800158A40683010A950108'],
     6: ['800111A406830101950108', '80014AA40683010A950108'],
     7: ['800103A406830101950108', '800158A40683010A950108', '840132A406830101950108'],
     8: ['800101A406830101950108', '800102A406830181950108', '800158A40683010A950108'],
     9: ['8001019000', '80011AA406830101950108', '800140A40683010A950108'],
    10: ['8001019000', '80015AA40683010A950108'],
    11: ['8001019000', '800118A40683010A950108', '8001429700'],
    12: ['800101A406830101950108', '80015A9700'],
    13: ['800113A406830101950108', '800148A40683010A950108'],
    14: ['80015EA40683010A950108'],
}

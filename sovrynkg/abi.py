# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/abi.ipynb (unless otherwise specified).

__all__ = ['load_abis_from_file', 'keccak', 'ABIDIR', 'SignatureDoesNotMatch', 'IndexingWithNonIndexedInput', 'ABI_IO',
           'ABI', 'ABIS', 'load_abi_dir', 'load_abi_dirs', 'allabis', 'KNOWN', 'lookup_from_topic', 'decode_log']

# Cell
import os
import json
from binascii import unhexlify, hexlify
from pathlib import Path
import traceback

from pydantic import BaseModel, ValidationError, Extra
from typing import List, Optional
import sha3
from eth_abi import decode_single

# Cell
def load_abis_from_file(abi_file):
    with open(abi_file) as f:
        return json.load(f)

def keccak(inputstr):
    encoded = inputstr.encode()
    keccak = sha3.keccak_256()
    keccak.update(encoded)
    return keccak.hexdigest()

# Cell
ABIDIR = Path(os.environ.get("SOVRYN_ABI_DIR", "ABIs"))

# Cell

class SignatureDoesNotMatch(Exception):
    pass

class IndexingWithNonIndexedInput(Exception):
    pass

class ABI_IO(BaseModel):
    name: str
    type: str
    indexed: Optional[bool]
    internalType: Optional[str]

class ABI(BaseModel, extra=Extra.forbid):
    name: Optional[str]
    constant: Optional[bool]
    inputs: Optional[List[ABI_IO]]
    outputs: Optional[List[ABI_IO]]
    payable: Optional[bool]
    stateMutability: Optional[str]
    type: str
    anonymous: Optional[bool]

    def inputs_as_str(self, input_list=None):
        input_list = input_list or self.inputs
        input_list = [inp.type for inp in input_list]
        return ','.join(input_list)

    def indexed_inputs(self):
        return [inp for inp in self.inputs if inp.indexed]
    def unindexed_inputs(self):
        return [inp for inp in self.inputs if not inp.indexed]

    def signature(self) -> dict:
        if self.inputs is None:
            return None
        name = self.name
        plain = '{name}({inp})'.format(name=name, inp=self.inputs_as_str())
        return dict(plain=plain, hashed=keccak(plain))

    def check_signature(self, candidate_signature:str):
        this_signature = '0x'+self.signature()['hashed']
        if candidate_signature != this_signature:
            raise SignatureDoesNotMatch("ABI signature does not match {s} {th}".format(s=signature, th=this_signature))
        return True

    def decode_single(self, dtype:str, data:str):
        if data.startswith('0x'):
            data = data[2:]
        return decode_single(dtype, unhexlify(data))

    def decode_data(self, data):
        unindexed_inputs = self.unindexed_inputs()
        dtypes = '({})'.format(self.inputs_as_str(unindexed_inputs))
        result = self.decode_single(dtypes, data)
        unindexed_input_names = [inp.name for inp in unindexed_inputs]
        result_d = dict(zip(unindexed_input_names, result))
        return result_d

    def decode_indexed_data(self, indexed_data):
        decoded = {}
        indexed_inputs = self.indexed_inputs()
        for index, entry in enumerate(indexed_data):
            _input = indexed_inputs[index]
            if not _input.indexed:
                IndexingWithNonIndexedInput("{inp} is not an indexed input: {topics}".format(inp=_input, topics=topics))
            value = self.decode_single(_input.type, entry)
            decoded[_input.name] = value
        return decoded

    def separate_topic(self, topics):
        signature = topics[0]
        try:
            indexed_data = topics[1:]
        except KeyError:
            indexed_data = []
        return signature, indexed_data

    def decode_logs(self, topics, data):
        signature, indexed_data = self.separate_topic(topics)
        self.check_signature(signature)

        decoded = self.decode_indexed_data(indexed_data)
        if data is None:
            return decoded

        else:
            decoded_data = self.decode_data(data)
        decoded.update(decoded_data)
        return decoded

class ABIS(BaseModel):
    abis: List[ABI]
    @classmethod
    def load(clz, abi_file):
        abis = load_abis_from_file(abi_file)
        return clz(abis=abis)

    def filter_by_type(self, type_):
        matching = [abi for abi in self.abis if abi.type.upper()==type_.upper()]
        return ABIS(abis=matching)
    def events(self):
        return self.filter_by_type('event')
    def filter_by_name(self, name):
        matching = [abi for abi in self.abis if abi.name==name]
        return ABIS(abis=matching)

# Cell
def load_abi_dir(abi_dir):
    allabis = {}
    for fname in Path(abi_dir).iterdir():
        abis = ABIS.load(fname)
        allabis[str(fname.stem)] = abis
    return allabis

def load_abi_dirs(master_dir):
    '''
    load a directory of other directories.
        master dir
        ├── project1
        │   ├── abi_file.json
        │   ├── other_abi_file.json
        ├── project2
        │   ├── abi3.abi
        │   ├── abi4.abi
    '''
    nested_abis = {}
    for abi_dir in Path(master_dir).iterdir():
        if abi_dir.is_dir():
            nested_abis[abi_dir.stem] = load_abi_dir(abi_dir)

    return nested_abis
#abis = load_abi_dir(abidir.joinpath('oracle-based-amm'))

# Cell
allabis = load_abi_dirs(ABIDIR)
KNOWN = {}
for proj in allabis:
    for fname, abis in allabis[proj].items():
        for abi in abis.abis:
            sig = abi.signature()
            if sig is not None:
                KNOWN[sig['hashed']] = abi

# Cell
def lookup_from_topic(topic):
    ss = topic[:]
    ss = ss if not ss.startswith('0x') else ss[2:]
    return KNOWN.get(ss)

def decode_log(topics, data):
    abi = lookup_from_topic(topics[0])
    if abi is not None:
        return {'abi': abi, 'decoded': abi.decode_logs(topics, data)}
    else:
        return None

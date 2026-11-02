"""Cold, exact-build admission for packaged cross-platform native UI adapters.

No download, compilation, symbol scanning or scene mutation occurs at runtime.
The developer-built catalog pins both the manifest and library. Windows RVAs
come from the matching PDB and are validated against the complete host image.
"""
import ctypes as C
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import platform
import struct
from .bridge import BridgeUnavailable

ROOT = Path(__file__).resolve().parents[1] / '_native'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def platform_key(system, machine):
    aliases = {'AMD64': 'x86_64', 'amd64': 'x86_64', 'aarch64': 'arm64'}
    arch = aliases.get(machine, machine)
    if system not in {'Darwin', 'Windows', 'Linux'} or arch not in {'arm64', 'x86_64'}:
        raise BridgeUnavailable(f'Unsupported native UI platform: {system}/{machine}')
    return system.lower() + '-' + arch


def package(root, *, system, machine, build, backend, executable):
    """Validate all disk inputs before allowing any adapter code to load."""
    key = platform_key(system, machine) + '/' + build
    catalog = json.loads((root / 'catalog.json').read_text())
    if catalog.get('schema') != 1:
        raise BridgeUnavailable('Unsupported native catalog schema')
    entry = catalog.get('packages', {}).get(key)
    if entry is None:
        raise BridgeUnavailable(f'No packaged Beyond UI adapter for {key}')
    directory = (root / entry['directory']).resolve(strict=True)
    if not directory.is_relative_to(root.resolve()):
        raise BridgeUnavailable('Native UI package escapes its root')
    manifest_path = directory / 'manifest.json'
    if digest(manifest_path) != entry['manifest_sha256']:
        raise BridgeUnavailable('Native UI manifest fingerprint mismatch')
    manifest = json.loads(manifest_path.read_text())
    if (manifest['schema'] != 1 or manifest['abi'] != 'beyond-ui-portable-v1'
            or manifest['platform'] != platform_key(system, machine)
            or manifest['build_hash'] != build or backend not in manifest['backends']):
        raise BridgeUnavailable('Native UI platform/build/backend mismatch')
    if set(manifest['sources']) != {'bridge_portable.cpp'}:
        raise BridgeUnavailable('Native UI source inventory mismatch')
    for name, expected in manifest['sources'].items():
        path = (root / name).resolve(strict=True)
        if not path.is_relative_to(root.resolve()) or digest(path) != expected:
            raise BridgeUnavailable('Native UI source fingerprint mismatch')
    binary = (directory / manifest['library']).resolve(strict=True)
    if binary.parent != directory or digest(binary) != manifest['binary_sha256']:
        raise BridgeUnavailable('Native UI binary fingerprint mismatch')
    if digest(executable) != manifest['executable_sha256']:
        raise BridgeUnavailable('Native UI requires its exact stock Blender executable')
    return binary, manifest


def pe_sections(data):
    try:
        if data[:2] != b'MZ': raise ValueError('Not a PE image')
        pe = struct.unpack_from('<I', data, 0x3c)[0]
        if data[pe:pe+4] != b'PE\0\0': raise ValueError('Invalid PE signature')
        machine, count = struct.unpack_from('<HH', data, pe+4)
        size = struct.unpack_from('<H', data, pe+20)[0]
        if machine != 0x8664 or size < 112 or struct.unpack_from('<H', data, pe+24)[0] != 0x20b:
            raise ValueError('Native UI requires PE32+ AMD64')
        offset = pe+24+size
        if not 0 < count <= 96 or offset+40*count > len(data): raise ValueError('Invalid PE sections')
        rows=[]
        for index in range(count):
            pos=offset+40*index
            length, address=struct.unpack_from('<II',data,pos+8)
            flags=struct.unpack_from('<I',data,pos+36)[0]
            if address+length > 2**32: raise ValueError('PE section overflow')
            rows.append((address,address+length,flags))
        return rows
    except struct.error as error:
        raise ValueError('Truncated PE image') from error


def checked_windows_addresses(data, manifest):
    if hashlib.sha256(data).hexdigest() != manifest['executable_sha256']:
        raise ValueError('Windows executable fingerprint mismatch')
    sections=pe_sections(data)
    symbols=manifest['host_symbols'];rvas=manifest['windows']['function_rvas']
    if not symbols or len(symbols)>512 or len(set(symbols))!=len(symbols) or set(symbols)!=set(rvas):
        raise ValueError('Windows function inventory mismatch')
    result=[]
    for name in symbols:
        address=rvas[name]
        if type(address) is not int or not any(a<=address<b and f&0x20000000 for a,b,f in sections):
            raise ValueError('Windows function outside executable section: '+name)
        result.append(address)
    slot=manifest['windows']['free_slot_rva']
    if type(slot) is not int or not any(a<=slot and slot+8<=b and f&0x40000000 and not f&0x20000000 for a,b,f in sections):
        raise ValueError('Windows allocator slot outside data section')
    return result,slot


def open_library(binary, manifest, executable):
    if manifest['platform'].startswith('windows-'):
        kernel=C.WinDLL('kernel32',use_last_error=True)
        kernel.GetModuleHandleW.argtypes=[C.c_wchar_p];kernel.GetModuleHandleW.restype=C.c_void_p
        kernel.GetModuleFileNameW.argtypes=[C.c_void_p,C.c_wchar_p,C.c_uint];kernel.GetModuleFileNameW.restype=C.c_uint
        base=kernel.GetModuleHandleW(None);path=C.create_unicode_buffer(32768)
        size=kernel.GetModuleFileNameW(base,path,len(path))
        if not base or not 0<size<len(path) or Path(path.value).resolve()!=Path(executable).resolve():
            raise BridgeUnavailable('Could not verify the running Windows image')
        rvas,slot=checked_windows_addresses(Path(executable).read_bytes(),manifest)
        lib=C.PyDLL(str(binary))
        init=lib.bui_host_initialize;init.argtypes=[C.POINTER(C.c_void_p),C.c_uint];init.restype=C.c_int
        addresses=(C.c_void_p*len(rvas))(*(base+rva for rva in rvas))
        if init(addresses,len(rvas))!=1: raise BridgeUnavailable('Host function table rejected')
        free_slot=base+slot
    else:
        host=C.PyDLL(None)
        for name in manifest['host_symbols']:
            if not getattr(host,name,None): raise BridgeUnavailable('Missing host symbol: '+name)
        free_slot=C.addressof(C.c_void_p.in_dll(host,manifest['free_symbol']))
        lib=C.PyDLL(str(binary))
    lib.bui_bridge_abi.argtypes=[];lib.bui_bridge_abi.restype=C.c_int
    if lib.bui_bridge_abi()!=1: raise BridgeUnavailable('Native UI ABI mismatch')
    lib.bui_free_slot.argtypes=[C.c_void_p];lib.bui_free_slot.restype=None;lib.bui_free_slot(free_slot)
    return lib


@lru_cache(maxsize=1)
def load():
    try:
        import bpy
        import gpu
        backend = gpu.platform.backend_type_get() if not bpy.app.background else 'BACKGROUND'
        binary, manifest=package(ROOT,system=platform.system(),machine=platform.machine(),
            build=bpy.app.build_hash.decode(),backend=backend,executable=bpy.app.binary_path)
        return open_library(binary,manifest,bpy.app.binary_path),manifest
    except (ImportError,OSError,ValueError,KeyError,TypeError,AttributeError) as error:
        raise BridgeUnavailable(str(error)) from error

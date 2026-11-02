"""Developer-only exact-header native package builder; never invoked at runtime."""
import argparse,hashlib,json,os,platform,re,shutil,struct,subprocess,sys,tarfile,urllib.request,uuid,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def run(args, *, cwd=None, output=None):
    result=subprocess.run([str(a) for a in args],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    if output:Path(output).write_text(result.stdout,encoding='utf8')
    if result.returncode:
        print(result.stdout[-14000:],flush=True);result.check_returncode()
    return result.stdout

def download(url,target,expected=None):
    if not target.exists():
        print('Download',url,flush=True)
        with urllib.request.urlopen(url,timeout=120) as src,target.open('wb') as dst:shutil.copyfileobj(src,dst)
    if expected and sha(target)!=expected:raise ValueError('Download checksum mismatch: '+url)
    return target

def extract(archive,directory):
    directory.mkdir(parents=True,exist_ok=True)
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as f:f.extractall(directory)
    else:
        with tarfile.open(archive) as f:f.extractall(directory,filter='data')

def pe_identity(data):
    pe=struct.unpack_from('<I',data,0x3c)[0];count=struct.unpack_from('<H',data,pe+6)[0]
    opt=struct.unpack_from('<H',data,pe+20)[0];sections=[]
    for i in range(count):
        off=pe+24+opt+i*40;vsize,rva,rawsize,raw=struct.unpack_from('<4I',data,off+8);sections.append((rva,max(vsize,rawsize),raw))
    def file_offset(rva):
        for start,size,raw in sections:
            if start<=rva<start+size:return raw+rva-start
        raise ValueError('PE RVA outside file')
    debug,size=struct.unpack_from('<II',data,pe+24+112+6*8)
    for off in range(file_offset(debug),file_offset(debug)+size,28):
        kind,length,address,raw=struct.unpack_from('<4I',data,off+12)
        if kind==2 and data[raw:raw+4]==b'RSDS':
            return str(uuid.UUID(bytes_le=data[raw+4:raw+20])),struct.unpack_from('<I',data,raw+20)[0]
    raise ValueError('No matching PDB identity in executable')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--version',required=True);ap.add_argument('--workspace',type=Path,required=True)
    ap.add_argument('--blender',type=Path);ap.add_argument('--destination',type=Path,default=ROOT/'beyond_ui/_native/packages')
    args=ap.parse_args();work=args.workspace.resolve();work.mkdir(parents=True,exist_ok=True)
    version=args.version;major,minor,patch=map(int,version.split('.'));family=major*10+minor
    system=platform.system();arch={'AMD64':'x86_64','aarch64':'arm64'}.get(platform.machine(),platform.machine())
    key=system.lower()+'-'+arch
    if system=='Windows':suffix='windows-x64.zip'
    elif system=='Linux':suffix='linux-x64.tar.xz'
    elif system=='Darwin':suffix='macos-'+('arm64' if arch=='arm64' else 'x64')+'.dmg'
    else:raise ValueError('Unsupported build platform')
    blender=args.blender
    if blender is None:
        base=f'https://download.blender.org/release/Blender{major}.{minor}/'
        filename=f'blender-{version}-{suffix}'
        sums=urllib.request.urlopen(base+f'blender-{version}.sha256').read().decode()
        expected=next(line.split()[0] for line in sums.splitlines() if line.split()[-1].lstrip('*')==filename)
        archive=download(base+filename,work/filename,expected)
        directory=work/'runtime'
        if system=='Darwin':
            directory.mkdir(exist_ok=True);run(['hdiutil','attach','-readonly','-nobrowse','-mountpoint',directory,archive])
            blender=directory/'Blender.app/Contents/MacOS/Blender'
        else:
            if not directory.exists():extract(archive,directory)
            blender=next(directory.rglob('blender.exe' if system=='Windows' else 'blender'))
    blender=blender.resolve();identity=work/'runtime.json';profile=work/'profile';profile.mkdir(exist_ok=True)
    os.environ.update(BLENDER_USER_CONFIG=str(profile/'config'),BLENDER_USER_SCRIPTS=str(profile/'scripts'),BLENDER_USER_EXTENSIONS=str(profile/'extensions'))
    script=work/'identify.py';script.write_text('import bpy,json\nfrom pathlib import Path\nPath('+repr(str(identity))+').write_text(json.dumps(dict(version=list(bpy.app.version),build=bpy.app.build_hash.decode())))\n')
    run([blender,'--background','--factory-startup','--python-exit-code','1','--python',script],output=work/'identify.log')
    host=json.loads(identity.read_text());assert host['version']==[major,minor,patch],host
    build=host['build'];out=args.destination.resolve()/key/build;out.mkdir(parents=True,exist_ok=True)
    source=ROOT/'beyond_ui/_native/bridge_portable.cpp'
    archive=download('https://github.com/blender/blender/archive/'+build+'.tar.gz',work/'source.tar.gz')
    if not (work/'source').exists():extract(archive,work/'source')
    checkout=next((work/'source').iterdir())
    versions=(checkout/'build_files/build_environment/cmake/versions.cmake').read_text()
    fmt_version=re.search(r'set\(FMT_VERSION ([^)]+)\)',versions).group(1).strip('"')
    fmt_archive=download('https://github.com/fmtlib/fmt/archive/refs/tags/'+fmt_version+'.tar.gz',work/'fmt.tar.gz')
    if not (work/'fmt').exists():extract(fmt_archive,work/'fmt')
    fmt=next((work/'fmt').iterdir())/'include'
    interface=(checkout/'source/blender/editors/include/UI_interface_c.hh').read_text()
    memory=(checkout/'intern/guardedalloc/MEM_guardedalloc.h').read_text()
    flags={'BUI_FAMILY':family,'BUI_PYRNA_C':int((checkout/'source/blender/python/intern/bpy_rna.h').exists()),'BUI_OPTIONAL_LABELS':int('std::optional<blender::StringRef> str' in interface or family>=51),
           'BUI_FUNCTION_DRAW':int(bool(re.search(r'UI_but_func_drawextra_set\([^;]+std::function',interface,re.S))),
           'BUI_ENUM_EMBOSS':int('enum class EmbossType' in interface),'BUI_FREE_TYPED':int('mem_freeN_ex' in memory)}
    # Extract unchanged public declarations to avoid unrelated editor DNA/OIIO
    # dependencies. Types still come from this exact build's full DNA headers.
    screen=(checkout/'source/blender/editors/include/ED_screen.hh').read_text()
    names=['ED_region_blend_alpha','ED_screen_user_menus_find','ED_screen_user_menu_ensure',
           'ED_screen_user_menu_item_find_operator','ED_screen_user_menu_item_find_prop',
           'ED_screen_user_menu_item_add_operator','ED_screen_user_menu_item_add_prop',
           'ED_screen_user_menu_item_remove']
    declarations=[]
    for name in names:
        matches=re.findall(r'^[A-Za-z][^;{}\n]*\b'+name+r'\([^;{}]*\);',screen,re.M)
        if len(matches)!=1:raise ValueError('Cannot extract exact declaration: '+name)
        declarations.append(matches[0])
    threads=(checkout/'source/blender/blenlib/BLI_threads.h').read_text()
    declaration=re.search(r'^int BLI_thread_is_main\((?:void)?\);',threads,re.M)
    if declaration is None:raise ValueError('Missing main-thread declaration')
    thread_decl=declaration[0]
    if 'extern "C"' in threads:thread_decl='extern "C" '+thread_decl
    declarations.append(thread_decl)
    text='\n'.join(declarations)
    if family>=51:text='namespace blender {\n'+text+'\n}'
    (work/'bui_screen_declarations.hh').write_text('// SPDX-License-Identifier: GPL-2.0-or-later\n// Unchanged declarations from the exact Blender source archive.\n'+text+'\n')
    includes=[checkout/'source/blender'/p for p in ('blenlib','blenkernel','makesdna','makesrna','editors/include','windowmanager','gpu','blenfont','depsgraph')]
    includes += [checkout/'intern/guardedalloc',checkout/'intern/atomic',fmt,work]
    free_symbol=('?mem_freeN_ex@internal@mem_guarded@@3P6AXPEAXW4DestructorType@12@@ZEA' if flags['BUI_FREE_TYPED'] else 'MEM_freeN') if system=='Windows' else ('_ZN11mem_guarded8internal12mem_freeN_exE' if flags['BUI_FREE_TYPED'] else 'MEM_freeN')
    manifest=dict(schema=1,abi='beyond-ui-portable-v1',platform=key,build_hash=build,version=version,family=family,
        backends=['BACKGROUND']+(['METAL'] if system=='Darwin' else ['OPENGL']+(['VULKAN'] if family>=43 else [])),
        sources={'bridge_portable.cpp':sha(source)},executable_sha256=sha(blender),free_symbol=free_symbol,
        qualification='built-for-user-qa',compile_defines=flags,source_archive_sha256=sha(archive))
    if system=='Windows':
        obj=work/'bridge.obj';response=work/'compile.rsp'
        options=['/nologo','/c','/std:c++20','/O2','/MD','/EHsc','/DNDEBUG','/utf-8','/J','/DWIN32','/D_WIN32','/D_WINDOWS','/D__SSE2__']
        options += ['/D'+k+'='+str(v) for k,v in flags.items()]+['/I'+str(p) for p in includes]+[str(source),'/Fo'+str(obj)]
        response.write_text('\n'.join('"'+x+'"' for x in options))
        run(['cl.exe','@'+str(response)],output=work/'compile.log')
        dump=run(['dumpbin.exe','/symbols',obj],output=work/'symbols.txt')
        undefined={line.split('|',1)[1].strip().split(' ',1)[0] for line in dump.splitlines() if 'UNDEF' in line and 'External' in line and '|' in line}
        needed={name for name in undefined if name.startswith(('?','MEM_','BLI_','pyrna_')) and not name.startswith(('??','?__','?what@','?_','?terminate@'))}
        needed={name for name in needed if '@std@@' not in name and '__std_' not in name}
        requested=work/'requested.txt';requested.write_text('\n'.join(sorted(needed|{free_symbol})))
        vs=Path(os.environ['VSINSTALLDIR']);dia=vs/'DIA SDK';tool=work/'pdb_symbols.exe'
        run(['cl.exe','/nologo','/std:c++17','/EHsc','/MD','/O2','/I'+str(dia/'include'),ROOT/'tools/native/pdb_symbols.cpp','/Fe'+str(tool),'/link','/LIBPATH:'+str(dia/'lib/amd64'),'diaguids.lib','ole32.lib','oleaut32.lib'],cwd=work,output=work/'dia-build.log')
        pdb=blender.with_suffix('.pdb');guid,age=pe_identity(blender.read_bytes());mapping=work/'rvas.json'
        dll=next((dia/'bin').rglob('amd64/msdia140.dll'),None) or dia/'bin/amd64/msdia140.dll'
        if not dll.exists():dll=next(vs.rglob('msdia140.dll'))
        run([tool,dll,pdb,requested,'{'+guid+'}',str(age),mapping])
        found=json.loads(mapping.read_text());missing=needed-set(found)
        if missing:raise ValueError('PDB symbols missing: '+repr(sorted(missing)))
        symbols=sorted(needed);count=len(symbols)
        asm=['EXTERN bui_host_addresses:QWORD','.code'];aliases=[]
        for i,name in enumerate(symbols):
            label='bui_thunk_'+str(i);aliases.append('/ALTERNATENAME:'+name+'='+label)
            asm += ['PUBLIC '+label,label+' PROC','jmp QWORD PTR [bui_host_addresses+'+str(i*8)+']',label+' ENDP']
        asm+=['END'];(work/'host.asm').write_text('\n'.join(asm)+'\n')
        (work/'host.cpp').write_text('extern "C" { void *bui_host_addresses['+str(count)+'] = {}; __declspec(dllexport) int bui_host_initialize(void *const *p, unsigned n) { if (!p || n != '+str(count)+') return 0; for (unsigned i=0;i<n;++i) if (!p[i]) return 0; for (unsigned i=0;i<n;++i) bui_host_addresses[i]=p[i]; return 1; }}')
        run(['cl.exe','/nologo','/O2','/MD','/c',work/'host.cpp','/Fo'+str(work/'host.obj')])
        run(['ml64.exe','/nologo','/c','/Fo'+str(work/'thunks.obj'),work/'host.asm'])
        binary=out/'beyond-ui.dll'
        run(['link.exe','/NOLOGO','/DLL','/MACHINE:X64','/OUT:'+str(binary),obj,work/'host.obj',work/'thunks.obj',*aliases],output=work/'link.log')
        manifest.update(host_symbols=symbols,windows=dict(function_rvas={name:found[name] for name in symbols},free_slot_rva=found[free_symbol],pdb_guid=guid,pdb_age=age,pdb_sha256=sha(pdb)))
    else:
        binary=out/('beyond-ui.dylib' if system=='Darwin' else 'beyond-ui.so')
        options=['c++','-std=c++20','-O2','-DNDEBUG','-funsigned-char','-fPIC','-fvisibility=hidden']
        if family==42 and system=='Darwin':options+=['-fdelayed-template-parsing']
        options+=['-D'+k+'='+str(v) for k,v in flags.items()]+['-I'+str(p) for p in includes]
        options+=['-dynamiclib','-undefined','dynamic_lookup'] if system=='Darwin' else ['-shared']
        run([*options,source,'-o',binary],output=work/'compile.log')
        dump=run(['nm','-u',binary]);symbols=[]
        for line in dump.splitlines():
            name=line.split()[-1].split('@')[0]
            if system=='Darwin' and name.startswith('_'):name=name[1:]
            if name.startswith(('_Z','MEM_','BLI_','pyrna_')) and not name.startswith(('_ZSt','_ZNSt','_ZTI','_ZTV','_Zdl','_Zn')):symbols.append(name)
        manifest['host_symbols']=sorted(set(symbols))
        if system=='Darwin':run(['codesign','--force','--sign','-',binary])
    manifest.update(library=binary.name,binary_sha256=sha(binary))
    target=out/'manifest.json';target.write_text(json.dumps(manifest,indent=2)+'\n')
    catalog_path=ROOT/'beyond_ui/_native/catalog.json';catalog=json.loads(catalog_path.read_text())
    catalog['packages'][key+'/'+build]=dict(directory=out.relative_to(ROOT/'beyond_ui/_native').as_posix(),manifest_sha256=sha(target))
    catalog_path.write_text(json.dumps(catalog,indent=2)+'\n')
    (work/'build-result.json').write_text(json.dumps(dict(package=str(out),blender=str(blender),version=version,build_hash=build),indent=2))
    print('Built',out,flush=True)

if __name__=='__main__':main()

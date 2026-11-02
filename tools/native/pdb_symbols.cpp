// SPDX-License-Identifier: GPL-3.0-or-later
// Developer-only DIA reader. Never shipped or executed inside Blender.
#include <windows.h>
#include <dia2.h>
#include <fstream>
#include <iostream>
#include <string>
#include <set>
#include <map>
#include <vector>
static std::string utf8(const wchar_t *s) {
 int n=WideCharToMultiByte(CP_UTF8,0,s,-1,nullptr,0,nullptr,nullptr); std::vector<char> v(n);
 WideCharToMultiByte(CP_UTF8,0,s,-1,v.data(),n,nullptr,nullptr);return std::string(v.data());
}
static void quote(const std::string &s) {
 std::cout << '"';for(char c:s) { if(c=='"'||c=='\\')std::cout<<'\\';std::cout<<c; }std::cout<<'"';
}
int wmain(int argc,wchar_t **argv) {
 if(argc!=7)return 2;CoInitialize(nullptr);
 HMODULE dll=LoadLibraryW(argv[1]);if(!dll)return 3;
 auto get=reinterpret_cast<HRESULT(WINAPI*)(REFCLSID,REFIID,void**)>(GetProcAddress(dll,"DllGetClassObject"));
 IClassFactory *factory=nullptr;IDiaDataSource *source=nullptr;
 if(!get||FAILED(get(__uuidof(DiaSource),IID_IClassFactory,reinterpret_cast<void**>(&factory))))return 4;
 if(FAILED(factory->CreateInstance(nullptr,__uuidof(IDiaDataSource),reinterpret_cast<void**>(&source))))return 5;
 GUID guid;if(FAILED(CLSIDFromString(argv[4],&guid)))return 6;
 if(FAILED(source->loadAndValidateDataFromPdb(argv[2],&guid,0,_wtoi(argv[5]))))return 7;
 std::ifstream input(argv[3]);std::set<std::string> wanted;std::string line;
 while(std::getline(input,line))if(!line.empty())wanted.insert(line);
 IDiaSession *session=nullptr;IDiaSymbol *global=nullptr;IDiaEnumSymbols *symbols=nullptr;
 if(FAILED(source->openSession(&session))||FAILED(session->get_globalScope(&global)))return 8;
 if(FAILED(global->findChildren(SymTagPublicSymbol,nullptr,nsNone,&symbols)))return 9;
 std::map<std::string,DWORD> found;IDiaSymbol *symbol=nullptr;ULONG count=0;
 while(SUCCEEDED(symbols->Next(1,&symbol,&count))&&count) {
  BSTR name=nullptr;DWORD rva=0;
  if(SUCCEEDED(symbol->get_name(&name))&&name) {
   std::string key=utf8(name);
   if(wanted.count(key)&&SUCCEEDED(symbol->get_relativeVirtualAddress(&rva))) {
    if(found.count(key)&&found[key]!=rva)return 10; found[key]=rva;
   }
   SysFreeString(name);
  }
  symbol->Release();
 }
 std::ofstream output(argv[6]);auto *old=std::cout.rdbuf(output.rdbuf());std::cout<<'{';bool first=true;
 for(auto &pair:found) { if(!first)std::cout<<',';first=false;quote(pair.first);std::cout<<':'<<pair.second; }
 std::cout<<'}';std::cout.rdbuf(old);
 symbols->Release();global->Release();session->Release();source->Release();factory->Release();CoUninitialize();return 0;
}

"""Compare unstripped C and Python builds of the original chibicc sources.

Original chibicc copyright (c) 2019 Rui Ueyama. See LICENSE.
This is a verification tool; the Python compiler never invokes the C compiler.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, output, label):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=300)
    (output / (label + '.stdout')).write_text(result.stdout)
    (output / (label + '.stderr')).write_text(result.stderr)
    if result.returncode:
        raise RuntimeError(f"{label} failed ({result.returncode}): {result.stderr}")
    return result.stdout


def locations(path):
    return [line.strip() for line in path.read_text().splitlines()
            if line.strip().startswith('.loc ')]


def verify(compilers, output, existing=None):
    output.mkdir(parents=True, exist_ok=True)
    work = output / 'work'
    work.mkdir(exist_ok=True)
    native_directory = output / 'native'
    native_directory.mkdir(exist_ok=True)
    shutil.copytree(ROOT / 'include', native_directory / 'include', dirs_exist_ok=True)
    native = native_directory / 'chibicc'
    sources = sorted(ROOT.glob('*.c'))
    run(['gcc', '-std=c11', '-g', '-fno-common', '-Wall', '-Wno-switch',
         '-o', str(native), *map(str, sources)], output, 'native-build')
    print('Built the original C compiler with GCC.', flush=True)
    report = {
        'source_sha256': {path.name: digest(path) for path in [*sources, ROOT / 'chibicc.h']},
        'cwd': str(ROOT),
        'gcc': run(['gcc', '--version'], output, 'gcc-version').splitlines()[0],
        'compile_flags': ['-fno-common', '-I' + str(ROOT / 'include'), '-S'],
        'link_flags': ['-g', '-Wl,-z,noexecstack'],
        'builds': {},
    }
    builds = [('reference', [str(native)])]
    builds += [(f'python-{index}', [sys.executable, str(compiler)])
               for index, compiler in enumerate(compilers, 1)]
    passed = True
    for label, compiler in builds:
        archive = output / label
        archive.mkdir(exist_ok=True)
        shutil.copytree(ROOT / 'include', archive / 'include', dirs_exist_ok=True)
        entry = {'compiler': compiler, 'sources': {}}
        report['builds'][label] = entry
        for source in sources:
            assembly = work / (source.stem + '.s')
            obj = work / (source.stem + '.o')
            run([*compiler, *report['compile_flags'], '-o', str(assembly), str(source)],
                output, label + '-' + source.stem + '-compile')
            run(['gcc', '-c', '-o', str(obj), str(assembly)],
                output, label + '-' + source.stem + '-assemble')
            shutil.copyfile(assembly, archive / assembly.name)
            shutil.copyfile(obj, archive / obj.name)
            if label != 'reference':
                reference = output / 'reference'
                checks = {'object_equal': obj.read_bytes() == (reference / obj.name).read_bytes(),
                          'debug_locations_equal': locations(assembly) == locations(reference / assembly.name)}
                entry['sources'][source.name] = checks
                passed = passed and all(checks.values())
                print(label, source.name, checks, flush=True)
        executable = work / 'chibicc'
        run(['gcc', *report['link_flags'], '-o', str(executable),
             *[str(work / (source.stem + '.o')) for source in sources]], output, label + '-link')
        shutil.copy2(executable, archive / 'chibicc')
        entry['sha256'], entry['size'] = digest(executable), executable.stat().st_size
        sections = run(['readelf', '-W', '-S', str(executable)], output, label + '-sections')
        symbols = run(['nm', '-u', str(executable)], output, label + '-symbols')
        entry['debug_information_present'] = all(name in sections for name in
                                                ('.debug_info', '.debug_line', '.symtab'))
        entry['assertions_present'] = '__assert_fail' in symbols
        passed = passed and entry['debug_information_present'] and entry['assertions_present']
        if label != 'reference':
            entry['executable_equal'] = executable.read_bytes() == (output / 'reference/chibicc').read_bytes()
            passed = passed and entry['executable_equal']
        run([str(archive / 'chibicc'), '-hashmap-test'], output, label + '-hashmap-test')
        sample = work / 'sample.c'
        sample.write_text('int main(void) { return 42; }\n')
        run([str(archive / 'chibicc'), '-S', '-o', str(work / 'sample.s'), str(sample)],
            output, label + '-sample-compile')
        run(['gcc', '-Wl,-z,noexecstack', '-o', str(work / 'sample'), str(work / 'sample.s')],
            output, label + '-sample-link')
        entry['sample_exit_status'] = subprocess.run([str(work / 'sample')], timeout=5).returncode
        passed = passed and entry['sample_exit_status'] == 42
        print(label, entry['size'], entry['sha256'], flush=True)
    if existing is not None:
        report['existing_reference'] = {'path': str(existing), 'sha256': digest(existing),
                                      'equal': existing.read_bytes() == (output / 'reference/chibicc').read_bytes()}
        passed = passed and report['existing_reference']['equal']
    report['passed'] = passed
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS' if passed else 'FAIL', output / 'report.json', flush=True)
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path, action='append',
                        help='Python compiler script/archive; repeat to check multiple builds')
    parser.add_argument('--output', type=Path, default=ROOT / 'python/build/bootstrap')
    parser.add_argument('--existing', type=Path, help='Also compare a previously built reference executable')
    options = parser.parse_args()
    compilers = [path.resolve() for path in (options.compiler or [ROOT / 'python/main.py'])]
    return verify(compilers, options.output.resolve(), options.existing.resolve() if options.existing else None)


if __name__ == '__main__':
    raise SystemExit(main())

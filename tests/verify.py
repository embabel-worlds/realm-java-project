#!/usr/bin/env python3
"""The battery. See tests/verify.sh for the layers and how to run it.

Every figure is judged against the repository read directly at the same commit, never against the
realm's own earlier answer.
"""
import base64, collections, json, os, re, subprocess, sys, tempfile, urllib.request
import xml.etree.ElementTree as ET
import yaml

REPO = 'https://github.com/spring-projects/spring-petclinic'
SHA = '500158f732419217507c7656904b8e6aa1bcc0d6'
PROJECT = f'{REPO}@{SHA}'
BASE = os.environ.get('APPLIANCE', 'http://127.0.0.1:8080').rstrip('/')
CREDS = os.environ.get('AUTH') or os.environ.get('EMBABEL_AUTH')
if not CREDS: sys.exit('set AUTH=user:pass')
JVM = {'java', 'kt', 'kts', 'groovy', 'scala'}

def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers={
        'Content-Type': 'application/json', 'Authorization': 'Basic ' + base64.b64encode(CREDS.encode()).decode()})
    with urllib.request.urlopen(req, timeout=900) as r: return json.loads(r.read().decode())

fails = []
def check(cond, label, detail=''):
    print(('ok   ' if cond else 'FAIL ') + label + (f'  [{detail}]' if detail and not cond else ''), flush=True)
    if not cond: fails.append(label)

def view(name, args):
    try:
        d = post(f'/api/v1/admin/kg/views/{name}/run', {'args': args})
    except Exception as e:  # an HTTP error is a refusal, reported as the view's failure
        check(False, f'L1 {name} answers', str(e)[:300]); return None
    err = d.get('error')
    check(not err, f'L1 {name} answers', str(err)[:300])
    if not d.get('rows'):  # an empty answer says why in its envelope; keep that beside any failure
        print(f'     {name} answered no rows: ' + json.dumps({k: v for k, v in d.items() if k != 'rows'})[:1500], flush=True)
    return d.get('rows') or []

# ---- L0: the repository at the commit --------------------------------------------------------
work = tempfile.mkdtemp(prefix='java-project-truth-')
subprocess.run(['git', 'clone', '-q', '--no-checkout', REPO + '.git', work], check=True)
subprocess.run(['git', '-C', work, 'checkout', '-q', SHA], check=True)
paths = subprocess.run(['git', '-C', work, 'ls-tree', '-r', '--name-only', SHA], check=True,
                       capture_output=True, text=True).stdout.split()
def text(p): return open(os.path.join(work, p), encoding='utf-8', errors='replace').read()
def ext(p): return p.rsplit('/', 1)[-1].rsplit('.', 1)[-1].lower() if '.' in p.rsplit('/', 1)[-1] else ''
def source_set(p):
    q = '/' + p
    return q.split('/src/', 1)[1].split('/')[0] if '/src/' in q else None
java = [p for p in paths if ext(p) == 'java']
jvm_src = [p for p in paths if ext(p) in JVM and source_set(p) is not None]
def package_of(p):
    parts = ('/' + p).split('/src/', 1)[1].split('/')
    return '.'.join(parts[2:-1])

pom = ET.fromstring(text('pom.xml'))
ns = {'m': pom.tag.split('}')[0].strip('{')}
def pt(e, tag): x = e.find(f'm:{tag}', ns); return x.text.strip() if x is not None and x.text else None
coords = f"{pt(pom, 'groupId')}:{pt(pom, 'artifactId')}:{pt(pom, 'version')}"
# The tree is the runtime classpath (compile and runtime scope), as `mvn dependency:tree -Dscope=runtime`
# prints it: a test-scoped declaration is not in it.
declared = {f"{pt(d, 'groupId')}:{pt(d, 'artifactId')}" for d in pom.findall('m:dependencies/m:dependency', ns)
            if pt(d, 'scope') != 'test'}

def flatten(prefix, v, out):
    if isinstance(v, dict):
        for k, x in v.items(): flatten(f'{prefix}.{k}' if prefix else str(k), x, out)
    elif isinstance(v, list):
        for i, x in enumerate(v): flatten(f'{prefix}[{i}]', x, out)
    else: out.append(prefix)
setting_keys = []
for p in paths:
    if ext(p) == 'properties':
        for line in text(p).splitlines():
            s = line.strip()
            if s and s[0] not in '#!':
                setting_keys.append(re.split(r'\s*[=:]\s*|\s+', s, maxsplit=1)[0])
    elif ext(p) in ('yml', 'yaml'):
        try:
            for doc in yaml.safe_load_all(text(p)):
                if doc is not None: flatten('', doc, setting_keys)
        except yaml.YAMLError:
            pass
spring_keys = sorted(k for k in setting_keys if k.startswith('spring.'))
spring_imports = sum(len(re.findall(r'(?m)^\s*import\s+(?:static\s+)?org\.springframework\.', text(p))) for p in java)
entity = sum(len(re.findall(r'@Entity\b', text(p))) for p in java)
print(f'L0 {PROJECT}: {len(paths)} files, {len(java)} java, {coords}, {len(declared)} declared, '
      f'{spring_imports} spring imports, {entity} @Entity, {len(spring_keys)} spring.* settings', flush=True)

# ---- L1 + L2 ----------------------------------------------------------------------------------
P = {'project': PROJECT}
rows = view('ProjectOverview', P)
if rows is not None:
    check(len(rows) == 1 and SHA in str(rows[0].get('project')), 'L2 ProjectOverview reads the pinned commit', rows)
    check(rows and rows[0].get('moduleCount') == 1 and rows[0].get('modules') == [coords], 'L2 ProjectOverview modules', rows)

rows = view('ProjectModules', P)
if rows is not None:
    check([(r.get('module'), r.get('coordinates')) for r in rows] == [('', coords)], 'L2 ProjectModules = the POM', rows)

rows = view('FilesByExtension', P)
if rows is not None:
    by = {r['extension']: r for r in rows}
    j = by.get('java') or {}
    want_main = sum(1 for p in java if '/src/main/' in '/' + p)
    want_test = sum(1 for p in java if '/src/test/' in '/' + p)
    check((j.get('files'), j.get('mainFiles'), j.get('testFiles')) == (len(java), want_main, want_test),
          'L2 FilesByExtension java files, main, test', f'{j} vs {(len(java), want_main, want_test)}')
    want = collections.Counter(ext(p) for p in paths if ext(p))
    for e, n in want.most_common(5):
        check((by.get(e) or {}).get('files') == n, f'L2 FilesByExtension {e} = {n}', by.get(e))

# The file listing read cold, past any kept read, so a kept empty answer cannot hide a live one.
try:
    d = post('/api/v1/admin/kg/execute', {'cypher':
        f"MATCH (p:JavaProject {{key: '{PROJECT}'}})-[:HAS_FILE {{ai: {{fresh: true}}}}]->(f:ProjectFile) RETURN count(f) AS files"})
    got = (d.get('rows') or [{}])[0].get('files')
    check(got == len(paths), 'L2 HAS_FILE read fresh = every file at the commit', f'{got} vs {len(paths)}; ' +
          json.dumps({k: v for k, v in d.items() if k != 'rows'})[:1500])
except Exception as e:
    check(False, 'L2 HAS_FILE read fresh answers', str(e)[:300])

rows = view('ModuleSources', P)
if rows is not None:
    r = next((r for r in rows if r.get('module') == ''), {})
    want = (sum(1 for p in jvm_src if source_set(p) == 'main'), sum(1 for p in jvm_src if source_set(p) == 'test'))
    check((r.get('mainFiles'), r.get('testFiles')) == want, 'L2 ModuleSources main/test files', f'{r} vs {want}')

rows = view('ModulePackages', P)
if rows is not None:
    got = {(r['sourceSet'], r['package']): r['files'] for r in rows}
    want = collections.Counter((source_set(p), package_of(p)) for p in jvm_src)
    check(got == dict(want), 'L2 ModulePackages packages and file counts', f'{len(got)} vs {len(want)}')

PKG = 'org.springframework.samples.petclinic.owner'
rows = view('PackageFiles', dict(P, package=PKG))
if rows is not None:
    want = sorted(p.rsplit('/', 1)[-1] for p in jvm_src if source_set(p) == 'main' and package_of(p) == PKG)
    check(sorted(r['file'] for r in rows) == want, f'L2 PackageFiles {PKG}', f'{len(rows)} vs {len(want)}')

rows = view('UsesOfPackage', dict(P, prefix='org.springframework.'))
if rows is not None:
    check(len(rows) == spring_imports, 'L2 UsesOfPackage org.springframework. = import lines', f'{len(rows)} vs {spring_imports}')

rows = view('AnnotatedWith', dict(P, annotation='Entity'))
if rows is not None:
    check(len(rows) == entity, 'L2 AnnotatedWith Entity = @Entity in the source', f'{len(rows)} vs {entity}')

rows = view('SettingsNamed', dict(P, prefix='spring.'))
if rows is not None:
    check(sorted(r['key'] for r in rows) == spring_keys, 'L2 SettingsNamed spring. = keys in .properties and YAML',
          f'{len(rows)} vs {len(spring_keys)}')

rows = view('DependencyTree', P)
if rows is not None:
    roots = [r for r in rows if r.get('depth') == 0]
    check([r.get('coordinates') for r in roots] == [coords], 'L2 DependencyTree root is the module', roots)
    direct = {':'.join(r['coordinates'].split(':')[:2]) for r in rows if r.get('depth') == 1}
    check(declared <= direct, 'L2 DependencyTree depth 1 holds every dependency the POM declares', sorted(declared - direct))

rows = view('WhyIsItHere', dict(P, artifact='spring-boot-starter-webmvc'))
if rows is not None:
    check(rows and min(r['depth'] for r in rows) == 1, 'L2 WhyIsItHere spring-boot-starter-webmvc is declared directly', rows[:3])

rows = view('VersionOf', dict(P, artifact='org.springframework:spring-core'))
if rows is not None:
    r = rows[0] if rows else {}
    check(r.get('resolved') and set(r['resolved']) <= set(r.get('managed') or []),
          'L2 VersionOf spring-core resolves to the version its BOM manages', r)

print(f'{len(fails)} failure(s)' if fails else 'ALL CHECKS PASS', flush=True)
sys.exit(1 if fails else 0)
